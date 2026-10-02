"""Run Manager - Durable workflow execution with PostgreSQL checkpointing."""

from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Union

import structlog
from langchain_core.messages import HumanMessage
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.store.base import BaseStore

from agenticai_sdk.config.schemas import AgenticAIConfig
from agenticai_sdk.schemas.workflow import WorkflowSchema
from agenticai_sdk.state.workflow_state import WorkflowState
from agenticai_sdk.runtime.postgres_checkpointer import PostgresCheckpointer
from agenticai_sdk.compiler import Compiler, CompilationResult
from agenticai_sdk.runtime.orchestrator import Orchestrator

logger = structlog.get_logger(__name__)


class RunError(Exception):
    """Raised when workflow execution fails."""
    pass


class RunManager:
    """Manages durable workflow execution with PostgreSQL checkpointing.
    
    Handles:
    - Workflow compilation
    - Execution with PostgreSQL checkpointer
    - HITL pause/resume
    - Run state persistence
    - Token/cost tracking
    """
    
    def __init__(
        self,
        config: AgenticAIConfig,
        checkpointer: Optional[BaseCheckpointSaver] = None,
        store: Optional[BaseStore] = None,
        compiler: Optional[Compiler] = None,
    ):
        self.config = config
        self.checkpointer = checkpointer
        self.store = store
        self.compiler = compiler or Compiler()
        self.orchestrator = Orchestrator()
        
        self._active_runs: Dict[str, Dict[str, Any]] = {}
    
    async def initialize(self) -> None:
        """Initialize run manager and dependencies."""
        # Initialize checkpointer if not provided
        if self.checkpointer is None:
            db_url = self.config.platform.database_url
            if db_url and "postgresql" in db_url:
                self.checkpointer = await PostgresCheckpointer.create(db_url)
        
        logger.info("run_manager_initialized", 
                   has_checkpointer=self.checkpointer is not None,
                   has_store=self.store is not None)
    
    async def close(self) -> None:
        """Clean up resources."""
        if self.checkpointer and hasattr(self.checkpointer, 'close'):
            await self.checkpointer.close()
    
    async def run(
        self,
        workflow: WorkflowSchema,
        input_message: str,
        thread_id: Optional[str] = None,
        initial_state: Optional[Dict[str, Any]] = None,
        workflow_revision_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Execute a workflow with durable checkpointing.
        
        Args:
            workflow: WorkflowSchema to execute
            input_message: Initial input message
            thread_id: Optional thread ID for checkpointing (auto-generated if not provided)
            initial_state: Optional initial state overrides
            workflow_revision_id: Optional workflow revision ID for audit
        
        Returns:
            Execution result with final state
        """
        thread_id = thread_id or str(uuid.uuid4())
        start_time = datetime.now(timezone.utc)
        
        logger.info("run_started", 
                   workflow_id=workflow.workflow_id,
                   thread_id=thread_id,
                   revision_id=workflow_revision_id)
        
        try:
            # Compile workflow
            compilation = self.compiler.compile(config_dict=workflow.model_dump())
            if not compilation.success:
                raise RunError(f"Compilation failed: {compilation.errors}")
            
            graph = compilation.graph
            
            # Prepare initial state
            initial_state_dict: WorkflowState = {
                "messages": [HumanMessage(content=input_message)],
                "scratchpad": initial_state.get("scratchpad", {}) if initial_state else {},
                "retrieved_context": [],
                "inner_thoughts": [],
                "next_step": None,
                "middleware_metadata": {},
                "trace_id": str(uuid.uuid4()),
                "workflow_id": workflow.workflow_id,
                "thread_id": thread_id,
                "workflow_revision_id": workflow_revision_id,
            }
            
            if initial_state:
                initial_state_dict.update(initial_state)
            
            config = {"configurable": {"thread_id": thread_id}}
            
            # Execute with checkpointing
            final_state = await graph.ainvoke(initial_state_dict, config=config)
            
            # Get final checkpoint
            checkpoint_tuple = None
            if self.checkpointer:
                checkpoint_tuple = await self.checkpointer.aget_tuple({
                    "configurable": {"thread_id": thread_id}
                })
            
            end_time = datetime.now(timezone.utc)
            duration_ms = int((end_time - start_time).total_seconds() * 1000)
            
            result = {
                "thread_id": thread_id,
                "status": "completed",
                "messages": final_state.get("messages", []),
                "scratchpad": final_state.get("scratchpad", {}),
                "retrieved_context": final_state.get("retrieved_context", []),
                "inner_thoughts": final_state.get("inner_thoughts", []),
                "next_step": final_state.get("next_step"),
                "duration_ms": duration_ms,
                "token_usage": final_state.get("token_usage", {}),
                "checkpoint_id": checkpoint_tuple.checkpoint["id"] if checkpoint_tuple else None,
            }
            
            logger.info("run_completed",
                       thread_id=thread_id,
                       status=result["status"],
                       duration_ms=duration_ms)
            
            return result
            
        except Exception as e:
            logger.error("run_failed", thread_id=thread_id, error=str(e))
            raise RunError(f"Workflow execution failed: {e}")
    
    async def run_with_revision(
        self,
        workflow_revision_id: str,
        input_message: str,
        thread_id: Optional[str] = None,
        initial_state: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Run a specific workflow revision by ID."""
        # TODO: Load revision from database
        # For now, assume workflow is passed directly
        raise NotImplementedError("Run by revision ID requires revision loading")
    
    async def resume(
        self,
        thread_id: str,
        workflow: WorkflowSchema,
        state_updates: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Resume a paused workflow from checkpoint.
        
        Args:
            thread_id: Thread ID to resume
            workflow: WorkflowSchema (must match checkpoint)
            state_updates: Optional state updates for HITL resume
        
        Returns:
            Execution result
        """
        logger.info("run_resumed", thread_id=thread_id)
        
        if not self.checkpointer:
            raise RunError("No checkpointer available for resume")
        
        try:
            compilation = self.compiler.compile(config_dict=workflow.model_dump())
            if not compilation.success:
                raise RunError(f"Compilation failed: {compilation.errors}")
            
            graph = compilation.graph
            
            config = {"configurable": {"thread_id": thread_id}}
            
            # Resume from checkpoint
            if state_updates:
                # Update state and continue
                final_state = await graph.ainvoke(state_updates, config=config)
            else:
                # Continue from checkpoint
                final_state = await graph.ainvoke(None, config=config)
            
            checkpoint_tuple = await self.checkpointer.aget_tuple({
                "configurable": {"thread_id": thread_id}
            })
            
            result = {
                "thread_id": thread_id,
                "status": "completed",
                "messages": final_state.get("messages", []),
                "scratchpad": final_state.get("scratchpad", {}),
                "retrieved_context": final_state.get("retrieved_context", []),
                "inner_thoughts": final_state.get("inner_thoughts", []),
                "next_step": final_state.get("next_step"),
                "checkpoint_id": checkpoint_tuple.checkpoint["id"] if checkpoint_tuple else None,
            }
            
            logger.info("run_resumed_completed", thread_id=thread_id)
            return result
            
        except Exception as e:
            logger.error("resume_failed", thread_id=thread_id, error=str(e))
            raise RunError(f"Resume failed: {e}")
    
    async def pause(self, thread_id: str) -> Dict[str, Any]:
        """Pause a running workflow (HITL pause)."""
        if not self.checkpointer:
            raise RunError("No checkpointer available")
        
        # The graph will pause at HITL nodes automatically
        # We just need to get the current checkpoint
        checkpoint_tuple = await self.checkpointer.aget_tuple({
            "configurable": {"thread_id": thread_id}
        })
        
        if not checkpoint_tuple:
            raise RunError(f"No checkpoint found for thread {thread_id}")
        
        return {
            "thread_id": thread_id,
            "status": "paused",
            "checkpoint_id": checkpoint_tuple.checkpoint["id"],
            "checkpoint_metadata": checkpoint_tuple.metadata,
        }
    
    async def get_run_status(self, thread_id: str) -> Dict[str, Any]:
        """Get current run status from checkpoint."""
        if not self.checkpointer:
            return {"thread_id": thread_id, "status": "unknown", "error": "No checkpointer"}
        
        checkpoint_tuple = await self.checkpointer.aget_tuple({
            "configurable": {"thread_id": thread_id}
        })
        
        if not checkpoint_tuple:
            return {"thread_id": thread_id, "status": "not_found"}
        
        checkpoint = checkpoint_tuple.checkpoint
        metadata = checkpoint_tuple.metadata
        
        return {
            "thread_id": thread_id,
            "status": metadata.get("status", "running"),
            "checkpoint_id": checkpoint["id"],
            "current_node": metadata.get("current_node"),
            "iteration": metadata.get("iteration", 0),
            "created_at": checkpoint_tuple.config.get("configurable", {}).get("checkpoint_id"),
        }
    
    async def list_checkpoints(self, thread_id: str) -> List[Dict[str, Any]]:
        """List all checkpoints for a thread."""
        if not self.checkpointer:
            return []
        
        tuples = await self.checkpointer.alist({
            "configurable": {"thread_id": thread_id}
        })
        
        return [
            {
                "checkpoint_id": t.checkpoint["id"],
                "thread_id": t.config["configurable"]["thread_id"],
                "metadata": t.metadata,
                "parent_checkpoint_id": t.parent_config["configurable"]["checkpoint_id"] if t.parent_config else None,
            }
            for t in tuples
        ]
    
    async def delete_thread(self, thread_id: str) -> bool:
        """Delete all checkpoints for a thread."""
        # This would require a DELETE operation on the checkpoints table
        # Implementation depends on checkpointer capabilities
        logger.warning("delete_thread_not_implemented", thread_id=thread_id)
        return False


async def create_run_manager(
    config: AgenticAIConfig,
    checkpointer: Optional[BaseCheckpointSaver] = None,
) -> RunManager:
    """Factory function to create and initialize RunManager."""
    manager = RunManager(config=config, checkpointer=checkpointer)
    await manager.initialize()
    return manager