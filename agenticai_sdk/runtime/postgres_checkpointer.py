"""PostgreSQL Checkpointer - LangGraph checkpoint persistence using PostgreSQL."""

from __future__ import annotations

import asyncio
import json
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple, AsyncIterator

import structlog
from sqlalchemy import create_engine, Column, String, DateTime, Text, Index, select
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, AsyncEngine
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.pool import NullPool

from langgraph.checkpoint.base import BaseCheckpointSaver, Checkpoint, CheckpointMetadata, CheckpointTuple
from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer

logger = structlog.get_logger(__name__)

Base = declarative_base()


class CheckpointModel(Base):
    """PostgreSQL table for LangGraph checkpoints."""
    __tablename__ = "langgraph_checkpoints"
    
    thread_id = Column(String(255), primary_key=True)
    checkpoint_ns = Column(String(255), primary_key=True, default="")
    checkpoint_id = Column(String(255), primary_key=True)
    parent_checkpoint_id = Column(String(255), nullable=True)
    checkpoint = Column(JSONB, nullable=False)
    checkpoint_checkpoint_metadata = Column(JSONB, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    
    __table_args__ = (
        Index("ix_checkpoints_thread_ns", "thread_id", "checkpoint_ns"),
    )


class PostgresCheckpointer(BaseCheckpointSaver):
    """PostgreSQL-based checkpoint saver for LangGraph.
    
    Provides durable, transactional checkpoint persistence with support for
    async operations and connection pooling.
    """
    
    def __init__(
        self,
        connection_string: str,
        serde: Optional[JsonPlusSerializer] = None,
        pool_size: int = 10,
        max_overflow: int = 20,
    ):
        super().__init__(serde=serde or JsonPlusSerializer())
        self.connection_string = connection_string
        self.pool_size = pool_size
        self.max_overflow = max_overflow
        self._engine: Optional[AsyncEngine] = None
        self._session_factory: Optional[sessionmaker] = None
    
    async def initialize(self) -> None:
        """Initialize database connection and create tables."""
        # Convert sync connection string to async
        async_conn_str = self.connection_string.replace("postgresql://", "postgresql+asyncpg://")
        
        self._engine = create_async_engine(
            async_conn_str,
            pool_size=self.pool_size,
            max_overflow=self.max_overflow,
            pool_pre_ping=True,
            echo=False,
        )
        
        self._session_factory = sessionmaker(
            self._engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )
        
        # Create tables
        async with self._engine.begin() as conn:
            await conn.run_sync(Base.checkpoint_metadata.create_all)
        
        logger.info("postgres_checkpointer_initialized", connection_string=self.connection_string)
    
    async def close(self) -> None:
        """Close database connections."""
        if self._engine:
            await self._engine.dispose()
            self._engine = None
            self._session_factory = None
            logger.info("postgres_checkpointer_closed")
    
    @asynccontextmanager
    async def _session(self) -> AsyncIterator[AsyncSession]:
        """Get database session."""
        if not self._session_factory:
            await self.initialize()
        
        async with self._session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()
    
    # --- BaseCheckpointSaver interface ---
    
    async def aput(
        self,
        config: Dict[str, Any],
        checkpoint: Checkpoint,
        checkpoint_metadata: CheckpointMetadata,
        new_versions: Dict[str, str],
    ) -> None:
        """Save checkpoint asynchronously."""
        async with self._session() as session:
            thread_id = config["configurable"]["thread_id"]
            checkpoint_ns = config["configurable"].get("checkpoint_ns", "")
            checkpoint_id = checkpoint["id"]
            parent_checkpoint_id = checkpoint.get("parent_id")
            
            # Serialize checkpoint and checkpoint_metadata
            checkpoint_data = self.serde.dumps(checkpoint)
            checkpoint_metadata_data = self.serde.dumps(checkpoint_metadata)
            
            # Upsert checkpoint
            stmt = select(CheckpointModel).where(
                CheckpointModel.thread_id == thread_id,
                CheckpointModel.checkpoint_ns == checkpoint_ns,
                CheckpointModel.checkpoint_id == checkpoint_id,
            )
            result = await session.execute(stmt)
            existing = result.scalar_one_or_none()
            
            if existing:
                existing.checkpoint = checkpoint_data
                existing.checkpoint_metadata = checkpoint_metadata_data
                existing.parent_checkpoint_id = parent_checkpoint_id
            else:
                new_checkpoint = CheckpointModel(
                    thread_id=thread_id,
                    checkpoint_ns=checkpoint_ns,
                    checkpoint_id=checkpoint_id,
                    parent_checkpoint_id=parent_checkpoint_id,
                    checkpoint=checkpoint_data,
                    checkpoint_metadata=checkpoint_metadata_data,
                )
                session.add(new_checkpoint)
            
            await session.commit()
    
    async def aput_writes(
        self,
        config: Dict[str, Any],
        writes: List[Tuple[str, Any, Any]],
        task_id: str,
    ) -> None:
        """Save writes associated with a checkpoint."""
        # Writes are stored in the checkpoint checkpoint_metadata
        # For simplicity, we update the latest checkpoint
        async with self._session() as session:
            thread_id = config["configurable"]["thread_id"]
            checkpoint_ns = config["configurable"].get("checkpoint_ns", "")
            
            # Get latest checkpoint
            stmt = select(CheckpointModel).where(
                CheckpointModel.thread_id == thread_id,
                CheckpointModel.checkpoint_ns == checkpoint_ns,
            ).order_by(CheckpointModel.created_at.desc()).limit(1)
            
            result = await session.execute(stmt)
            checkpoint = result.scalar_one_or_none()
            
            if checkpoint:
                # Update checkpoint_metadata with writes
                checkpoint_metadata = self.serde.loads(checkpoint.checkpoint_metadata)
                if "writes" not in checkpoint_metadata:
                    checkpoint_metadata["writes"] = []
                checkpoint_metadata["writes"].extend([
                    {"task_id": task_id, "channel": w[0], "value": w[2]} for w in writes
                ])
                checkpoint.checkpoint_metadata = self.serde.dumps(checkpoint_metadata)
                await session.commit()
    
    async def aget_tuple(self, config: Dict[str, Any]) -> Optional[CheckpointTuple]:
        """Get checkpoint tuple for a thread."""
        async with self._session() as session:
            thread_id = config["configurable"]["thread_id"]
            checkpoint_ns = config["configurable"].get("checkpoint_ns", "")
            checkpoint_id = config["configurable"].get("checkpoint_id")
            
            if checkpoint_id:
                stmt = select(CheckpointModel).where(
                    CheckpointModel.thread_id == thread_id,
                    CheckpointModel.checkpoint_ns == checkpoint_ns,
                    CheckpointModel.checkpoint_id == checkpoint_id,
                )
            else:
                # Get latest checkpoint
                stmt = select(CheckpointModel).where(
                    CheckpointModel.thread_id == thread_id,
                    CheckpointModel.checkpoint_ns == checkpoint_ns,
                ).order_by(CheckpointModel.created_at.desc()).limit(1)
            
            result = await session.execute(stmt)
            row = result.scalar_one_or_none()
            
            if not row:
                return None
            
            checkpoint = self.serde.loads(row.checkpoint)
            checkpoint_metadata = self.serde.loads(row.checkpoint_metadata)
            
            return CheckpointTuple(
                config={"configurable": {"thread_id": row.thread_id, "checkpoint_ns": row.checkpoint_ns, "checkpoint_id": row.checkpoint_id}},
                checkpoint=checkpoint,
                checkpoint_metadata=checkpoint_metadata,
                parent_config={"configurable": {"thread_id": row.thread_id, "checkpoint_ns": row.checkpoint_ns, "checkpoint_id": row.parent_checkpoint_id}} if row.parent_checkpoint_id else None,
            )
    
    async def alist(
        self,
        config: Dict[str, Any],
        before: Optional[Dict[str, Any]] = None,
        limit: Optional[int] = None,
    ) -> List[CheckpointTuple]:
        """List checkpoints for a thread."""
        async with self._session() as session:
            thread_id = config["configurable"]["thread_id"]
            checkpoint_ns = config["configurable"].get("checkpoint_ns", "")
            
            stmt = select(CheckpointModel).where(
                CheckpointModel.thread_id == thread_id,
                CheckpointModel.checkpoint_ns == checkpoint_ns,
            ).order_by(CheckpointModel.created_at.desc())
            
            if before and before.get("checkpoint_id"):
                stmt = stmt.where(CheckpointModel.checkpoint_id < before["checkpoint_id"])
            
            if limit:
                stmt = stmt.limit(limit)
            
            result = await session.execute(stmt)
            rows = result.scalars().all()
            
            tuples = []
            for row in rows:
                checkpoint = self.serde.loads(row.checkpoint)
                checkpoint_metadata = self.serde.loads(row.checkpoint_metadata)
                tuples.append(CheckpointTuple(
                    config={"configurable": {"thread_id": row.thread_id, "checkpoint_ns": row.checkpoint_ns, "checkpoint_id": row.checkpoint_id}},
                    checkpoint=checkpoint,
                    checkpoint_metadata=checkpoint_metadata,
                    parent_config={"configurable": {"thread_id": row.thread_id, "checkpoint_ns": row.checkpoint_ns, "checkpoint_id": row.parent_checkpoint_id}} if row.parent_checkpoint_id else None,
                ))
            
            return tuples
    
    # --- Sync versions (required by base class) ---
    
    def put(
        self,
        config: Dict[str, Any],
        checkpoint: Checkpoint,
        checkpoint_metadata: CheckpointMetadata,
        new_versions: Dict[str, str],
    ) -> None:
        """Sync version - runs async version in event loop."""
        asyncio.run(self.aput(config, checkpoint, checkpoint_metadata, new_versions))
    
    def put_writes(
        self,
        config: Dict[str, Any],
        writes: List[Tuple[str, Any, Any]],
        task_id: str,
    ) -> None:
        asyncio.run(self.aput_writes(config, writes, task_id))
    
    def get_tuple(self, config: Dict[str, Any]) -> Optional[CheckpointTuple]:
        return asyncio.run(self.aget_tuple(config))
    
    def list(
        self,
        config: Dict[str, Any],
        before: Optional[Dict[str, Any]] = None,
        limit: Optional[int] = None,
    ) -> List[CheckpointTuple]:
        return asyncio.run(self.alist(config, before, limit))


async def create_postgres_checkpointer(
    connection_string: str,
    **kwargs
) -> PostgresCheckpointer:
    """Factory function to create and initialize PostgresCheckpointer."""
    checkpointer = PostgresCheckpointer(connection_string, **kwargs)
    await checkpointer.initialize()
    return checkpointer