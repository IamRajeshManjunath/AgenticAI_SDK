"""Durable checkpoint storage used by workflow job workers."""

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from typing import Any, AsyncIterator

from sqlalchemy.engine import make_url

from agenticai_sdk.db.database import _load_config


def _database_url() -> str:
    configured = os.getenv("AGENTICAI_CHECKPOINT_DB_URL")
    if configured:
        return configured
    persisted = _load_config() or {}
    return (
        persisted.get("core_db_url")
        or os.getenv("AGENTICAI_DB_URL")
        or "sqlite:///agenticai.db"
    )


@asynccontextmanager
async def durable_checkpointer() -> AsyncIterator[Any]:
    """Open a persistent saver for the configured SQLite or PostgreSQL database."""
    database_url = _database_url()
    parsed = make_url(database_url)

    if parsed.get_backend_name() == "sqlite":
        from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

        path = parsed.database
        if path in (None, "", ":memory:"):
            raise RuntimeError("Durable worker checkpoints require a file-backed SQLite database.")
        async with AsyncSqliteSaver.from_conn_string(path) as saver:
            await saver.setup()
            yield saver
        return

    if parsed.get_backend_name() == "postgresql":
        from agenticai_sdk.runtime.postgres_checkpointer import PostgresCheckpointer

        saver = PostgresCheckpointer(database_url)
        await saver.initialize()
        try:
            yield saver
        finally:
            await saver.close()
        return

    raise RuntimeError(
        f"Workflow workers require SQLite or PostgreSQL checkpoint storage; got '{parsed.get_backend_name()}'."
    )
