"""Worker entrypoint for database-backed workflow jobs.

Run with ``python -m agenticai_sdk.worker`` alongside the API service.
"""

from __future__ import annotations

import asyncio
import logging
import os
import signal
import time
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

import structlog
from langchain_core.messages import HumanMessage
from sqlalchemy.orm import Session

from agenticai_sdk.db import get_session, init_db
from agenticai_sdk.db.models import WorkflowJob, WorkflowTrace
from agenticai_sdk.runtime.job_checkpointer import durable_checkpointer
from agenticai_sdk.runtime.job_queue import claim_next_job, fail_stale_jobs, heartbeat_job
from agenticai_sdk.runtime.orchestrator import Orchestrator
from agenticai_sdk.schemas.workflow import WorkflowSchema

logger = structlog.get_logger(__name__)


def _session() -> Session:
    return next(get_session())


def _serialize_messages(messages: list[Any]) -> list[dict[str, Any]]:
    serialized = []
    for message in messages:
        serialized.append({
            "type": getattr(message, "type", type(message).__name__.lower()),
            "content": getattr(message, "content", str(message)),
        })
    return serialized


class WorkflowJobWorker:
    def __init__(self, *, poll_seconds: float = 1.0, lease_seconds: int = 90) -> None:
        self.worker_id = f"worker-{uuid.uuid4().hex}"
        self.poll_seconds = poll_seconds
        self.lease_seconds = lease_seconds

    def recover_expired_jobs(self) -> int:
        db = _session()
        try:
            count = fail_stale_jobs(
                db,
                datetime.now(timezone.utc) - timedelta(seconds=self.lease_seconds),
            )
            if count:
                logger.warning("expired_workflow_jobs_failed", count=count)
            return count
        finally:
            db.close()

    def claim(self) -> dict[str, Any] | None:
        db = _session()
        try:
            job = claim_next_job(db, self.worker_id)
            if job is None:
                return None
            return {
                "id": job.id,
                "workspace_id": job.workspace_id,
                "workflow_id": job.workflow_id,
                "thread_id": job.thread_id,
                "workflow_config": job.workflow_config,
                "input_message": job.input_message,
                "initial_state": job.initial_state or {},
                "resume": bool(job.resume),
            }
        finally:
            db.close()

    async def _heartbeat(self, job_id: str, stop: asyncio.Event) -> None:
        interval = max(1, self.lease_seconds // 3)
        while not stop.is_set():
            try:
                await asyncio.wait_for(stop.wait(), timeout=interval)
            except asyncio.TimeoutError:
                db = _session()
                try:
                    if not heartbeat_job(db, job_id, self.worker_id):
                        logger.error("workflow_job_lease_lost", job_id=job_id)
                        return
                finally:
                    db.close()

    async def _execute(self, job: dict[str, Any]) -> None:
        job_id = job["id"]
        started = time.perf_counter()
        stop_heartbeat = asyncio.Event()
        heartbeat = asyncio.create_task(self._heartbeat(job_id, stop_heartbeat))
        status = "completed"
        output: dict[str, Any] = {}
        error_text: str | None = None
        try:
            workflow = WorkflowSchema.model_validate(job["workflow_config"])
            async with durable_checkpointer() as checkpointer:
                orchestrator = Orchestrator(checkpointer=checkpointer)
                graph = await orchestrator.compile(workflow)
                initial_state = None
                config = {"configurable": {"thread_id": job["thread_id"]}}
                if job["resume"]:
                    if job["initial_state"]:
                        await graph.aupdate_state(config, job["initial_state"])
                else:
                    initial_state = {
                        "messages": [HumanMessage(content=job["input_message"])],
                        "scratchpad": job["initial_state"].get("scratchpad", {}),
                        "retrieved_context": [],
                        "inner_thoughts": [],
                        "next_step": None,
                        "middleware_metadata": {},
                        "trace_id": None,
                        "workspace_id": job["workspace_id"],
                    }
                result = await graph.ainvoke(
                    initial_state,
                    config=config,
                )
                snapshot = await graph.aget_state(config)
                if snapshot.next:
                    status = "paused"
                output = {
                    "thread_id": job["thread_id"],
                    "status": status,
                    "messages": _serialize_messages((result or {}).get("messages", [])),
                    "scratchpad": (result or {}).get("scratchpad", {}),
                    "retrieved_context": (result or {}).get("retrieved_context", []),
                    "inner_thoughts": (result or {}).get("inner_thoughts", []),
                    "next_step": (result or {}).get("next_step"),
                }
        except Exception as exc:
            status = "failed"
            error_text = str(exc)
            logger.exception("workflow_job_execution_failed", job_id=job_id)
        finally:
            stop_heartbeat.set()
            await heartbeat

        duration_ms = round((time.perf_counter() - started) * 1000, 2)
        db = _session()
        try:
            persisted_job = db.query(WorkflowJob).filter(
                WorkflowJob.id == job_id,
                WorkflowJob.worker_id == self.worker_id,
                WorkflowJob.status == "running",
            ).first()
            if persisted_job is None:
                logger.error("workflow_job_result_discarded_after_lease_loss", job_id=job_id)
                return
            persisted_job.status = status
            persisted_job.result = output
            persisted_job.error = error_text
            persisted_job.completed_at = datetime.now(timezone.utc)
            persisted_job.updated_at = datetime.now(timezone.utc)
            trace_id = f"trace_{uuid.uuid4().hex}"
            db.add(WorkflowTrace(
                id=trace_id,
                trace_id=trace_id,
                workflow_id=job["workflow_id"],
                workspace_id=job["workspace_id"],
                duration_ms=duration_ms,
                total_tokens=0,
                cost_usd=0.0,
                error_count=1 if status == "failed" else 0,
                span_tree={
                    "job_id": job_id,
                    "thread_id": job["thread_id"],
                    "status": status,
                    "error": error_text,
                },
            ))
            db.commit()
        except Exception:
            db.rollback()
            logger.exception("workflow_job_result_persistence_failed", job_id=job_id)
            raise
        finally:
            db.close()

        logger.info("workflow_job_finished", job_id=job_id, status=status, duration_ms=duration_ms)

    async def run_once(self) -> bool:
        job = self.claim()
        if job is None:
            return False
        await self._execute(job)
        return True

    async def run_forever(self, stop: asyncio.Event) -> None:
        self.recover_expired_jobs()
        while not stop.is_set():
            if await self.run_once():
                continue
            try:
                await asyncio.wait_for(stop.wait(), timeout=self.poll_seconds)
            except asyncio.TimeoutError:
                pass


async def main() -> None:
    init_db()
    worker = WorkflowJobWorker(
        poll_seconds=float(os.getenv("WORKFLOW_WORKER_POLL_SECONDS", "1")),
        lease_seconds=int(os.getenv("WORKFLOW_WORKER_LEASE_SECONDS", "90")),
    )
    stop = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, stop.set)
        except NotImplementedError:
            signal.signal(
                sig,
                lambda _signal_number, _frame: loop.call_soon_threadsafe(stop.set),
            )
    logger.info("workflow_worker_started", worker_id=worker.worker_id)
    await worker.run_forever(stop)
    logger.info("workflow_worker_stopped", worker_id=worker.worker_id)


if __name__ == "__main__":
    logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
    asyncio.run(main())
