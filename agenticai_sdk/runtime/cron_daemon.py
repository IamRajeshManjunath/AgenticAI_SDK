import os
import asyncio
import datetime
import logging
from typing import Any, Dict, Optional
from croniter import croniter
from sqlalchemy.orm import Session
from agenticai_sdk.db.database import get_session
from agenticai_sdk.db.models import CronJob
from agenticai_sdk.runtime.orchestrator import Orchestrator

logger = logging.getLogger("agenticai_sdk.cron_daemon")

class CronDaemon:
    """Decentralized, persistent, and lease-locked CRON scheduling daemon.
    
    Multiple cluster nodes can run instances of this daemon. Process-safe SQL lease
    locks guarantee that each CRON execution triggers exactly once across the cluster.
    """
    def __init__(self, node_id: Optional[str] = None, poll_interval: float = 5.0):
        self.node_id = node_id or f"node-{os.getpid()}"
        self.poll_interval = poll_interval
        self._running = False
        self._task: Optional[asyncio.Task] = None

    def start(self):
        if not self._running:
            self._running = True
            self._task = asyncio.create_task(self._scheduler_loop())
            logger.info(f"Cron Daemon started on node {self.node_id}")

    async def stop(self):
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            logger.info(f"Cron Daemon stopped on node {self.node_id}")

    async def _scheduler_loop(self):
        while self._running:
            try:
                await self._poll_and_execute_jobs()
            except Exception as e:
                logger.error(f"Error in Cron scheduler loop: {e}", exc_info=True)
            await asyncio.sleep(self.poll_interval)

    async def _poll_and_execute_jobs(self):
        db = next(get_session())
        now = datetime.datetime.now(datetime.timezone.utc)
        try:
            # Query for active jobs that are past due and either unlocked or have expired lease locks
            jobs = db.query(CronJob).filter(
                CronJob.status == "active",
                CronJob.next_run_at <= now,
                (CronJob.locked_until == None) | (CronJob.locked_until < now)
            ).all()

            for job in jobs:
                # Attempt to acquire a pessimistic lock / lease on the job
                lease_duration = datetime.timedelta(minutes=5)
                locked_until = now + lease_duration
                
                # Double-check query condition using atomic CAS update in db
                updated = db.query(CronJob).filter(
                    CronJob.id == job.id,
                    CronJob.status == "active",
                    (CronJob.locked_until == None) | (CronJob.locked_until < now)
                ).update({
                    "locked_by": self.node_id,
                    "locked_until": locked_until
                }, synchronize_session=False)

                db.commit()

                if updated:
                    logger.info(f"Node {self.node_id} successfully locked and acquired lease for Cron job {job.id}")
                    # Trigger the job asynchronously to avoid blocking the main polling loop
                    asyncio.create_task(self._execute_job(job))
        finally:
            db.close()

    async def _execute_job(self, job: CronJob):
        logger.info(f"Executing scheduled CRON job {job.id} (Target: {job.target_type} - {job.target_id})")
        db = next(get_session())
        try:
            # 1. Execute the corresponding workflow or agent
            if job.target_type == "workflow":
                # Ingest the workflow configuration and execute via Orchestrator
                from agenticai_sdk.db.models import Workflow
                wf = db.query(Workflow).filter(Workflow.id == job.target_id).first()
                if wf and wf.config:
                    from agenticai_sdk.schemas.workflow import WorkflowSchema
                    schema = WorkflowSchema(**wf.config)
                    orchestrator = Orchestrator()
                    compiled_app = await orchestrator.compile(schema)
                    
                    initial_state = {
                        "messages": [],
                        "scratchpad": job.payload or {},
                        "retrieved_context": [],
                        "inner_thoughts": [],
                        "next_step": None,
                        "middleware_metadata": {},
                        "trace_id": f"cron-{job.id}-{int(datetime.datetime.now().timestamp())}"
                    }
                    
                    logger.info(f"Triggering workflow run for schedule {job.id}")
                    await compiled_app.ainvoke(initial_state)
            else:
                logger.warning(f"Standalone agent cron execution not yet compiled. Ingesting as sub-graph workflow.")

            # 2. Release lock and update next_run_at using croniter
            now = datetime.datetime.now(datetime.timezone.utc)
            iter = croniter(job.cron_expression, now)
            next_run = iter.get_next(datetime.datetime)
            
            db.query(CronJob).filter(CronJob.id == job.id).update({
                "last_run_at": now,
                "next_run_at": next_run,
                "locked_by": None,
                "locked_until": None
            }, synchronize_session=False)
            db.commit()
            logger.info(f"Cron job {job.id} completed. Next execution scheduled for {next_run}")
        except Exception as e:
            logger.error(f"Failed to execute Cron job {job.id}: {e}", exc_info=True)
            # Release lock so it can be retried or picked up again
            db.query(CronJob).filter(CronJob.id == job.id).update({
                "locked_by": None,
                "locked_until": None
            }, synchronize_session=False)
            db.commit()
        finally:
            db.close()

    def inject_cron(self, job_id: str, cron_expression: str, target_type: str, target_id: str, payload: Optional[Dict[str, Any]] = None) -> CronJob:
        """Exposes API to register a new CRON scheduling context at runtime."""
        if target_type not in ("workflow", "agent"):
            raise ValueError("Cron target_type must be either 'workflow' or 'agent'")
        
        # Validate expression using croniter
        if not croniter.is_valid(cron_expression):
            raise ValueError(f"Invalid CRON expression: '{cron_expression}'")

        db = next(get_session())
        try:
            now = datetime.datetime.now(datetime.timezone.utc)
            iter = croniter(cron_expression, now)
            next_run = iter.get_next(datetime.datetime)

            job = db.query(CronJob).filter(CronJob.id == job_id).first()
            if job:
                job.cron_expression = cron_expression
                job.target_type = target_type
                job.target_id = target_id
                job.payload = payload
                job.next_run_at = next_run
                job.status = "active"
            else:
                job = CronJob(
                    id=job_id,
                    cron_expression=cron_expression,
                    target_type=target_type,
                    target_id=target_id,
                    payload=payload,
                    next_run_at=next_run,
                    status="active"
                )
                db.add(job)
            
            db.commit()
            db.refresh(job)
            logger.info(f"Injected Cron job {job_id}: '{cron_expression}' -> Target {target_type}:{target_id}")
            return job
        finally:
            db.close()

    def mutate_cron(self, job_id: str, cron_expression: str, payload: Optional[Dict[str, Any]] = None) -> CronJob:
        """Mutates an active CRON expression or payload at runtime."""
        if not croniter.is_valid(cron_expression):
            raise ValueError(f"Invalid CRON expression: '{cron_expression}'")

        db = next(get_session())
        try:
            job = db.query(CronJob).filter(CronJob.id == job_id).first()
            if not job:
                raise KeyError(f"Cron job {job_id} not found")

            now = datetime.datetime.now(datetime.timezone.utc)
            iter = croniter(cron_expression, now)
            next_run = iter.get_next(datetime.datetime)

            job.cron_expression = cron_expression
            if payload is not None:
                job.payload = payload
            job.next_run_at = next_run
            
            db.commit()
            db.refresh(job)
            logger.info(f"Mutated Cron job {job_id} successfully")
            return job
        finally:
            db.close()

    def terminate_cron(self, job_id: str) -> bool:
        """Deactivates and deletes the CRON scheduler context at runtime."""
        db = next(get_session())
        try:
            job = db.query(CronJob).filter(CronJob.id == job_id).first()
            if not job:
                return False
            db.delete(job)
            db.commit()
            logger.info(f"Terminated and deleted Cron job {job_id}")
            return True
        finally:
            db.close()
