"""Compiler - Orchestrates the complete compilation pipeline.

Pipeline stages:
1. Parser - JSON -> Pydantic models
2. Schema Validator - JSON Schema + Pydantic validation
3. Semantic Validator - Deep semantic checks
4. Dependency Resolver - Topological sort, cycle detection
5. Graph Builder - LangGraph StateGraph construction
6. Middleware Injector - Lifecycle-aware middleware injection

Output: Compiled, executable LangGraph StateGraph
"""

from __future__ import annotations

import time
import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import structlog

from agenticai_sdk.config.loader import load_json_config, validate_json_schema
from agenticai_sdk.config.schemas import AgenticAIConfig
from agenticai_sdk.schemas.workflow import WorkflowSchema
from agenticai_sdk.compiler.parser import load_and_validate
from agenticai_sdk.compiler.schema_validator import SchemaValidator
from agenticai_sdk.compiler.semantic_validator import SemanticValidator
from agenticai_sdk.compiler.dependency_resolver import DependencyResolver, CycleDetectedError
from agenticai_sdk.compiler.graph_builder import GraphBuilder
from agenticai_sdk.compiler.middleware_injector import MiddlewareInjector

logger = structlog.get_logger(__name__)


@dataclass
class CompilationResult:
    """Result of compilation."""
    success: bool
    graph: Optional[Any] = None
    workflow: Optional[Any] = None
    config: Optional[Any] = None
    execution_order: Optional[List[str]] = None
    errors: List[str] = None
    warnings: List[str] = None
    compilation_time_ms: float = 0
    
    def __post_init__(self):
        if self.errors is None:
            self.errors = []
        if self.warnings is None:
            self.warnings = []


class Compiler:
    """Main compiler orchestrator."""
    
    def __init__(
        self,
        schema_path: Optional[Union[str, Path]] = None,
        checkpointer: Optional[Any] = None,
        store: Optional[Any] = None,
    ):
        self.schema_path = Path(schema_path) if schema_path else None
        self.checkpointer = checkpointer
        self.store = store
        self._compilation_cache: Dict[str, CompilationResult] = {}
    
    def compile(
        self,
        path: Optional[Union[str, Path]] = None,
        config_dict: Optional[Dict[str, Any]] = None,
        workflow_dict: Optional[Dict[str, Any]] = None,
        use_cache: bool = True,
    ) -> CompilationResult:
        """Compile workflow from file or dict.
        
        Args:
            path: Path to JSON config file (agenticai.json)
            config_dict: Pre-loaded config dict
            workflow_dict: Pre-loaded workflow dict (alternative to full config)
            use_cache: Whether to use compilation cache
        
        Returns:
            CompilationResult with compiled graph or errors
        """
        start_time = time.perf_counter()
        
        # Check cache
        cache_key = self._compute_cache_key(path, config_dict, workflow_dict)
        if use_cache and cache_key in self._compilation_cache:
            cached = self._compilation_cache[cache_key]
            logger.info("compilation_cache_hit", key=cache_key)
            return cached
        
        result = CompilationResult(success=False)
        
        try:
            # Stage 1: Parse & Load
            logger.info("compilation_stage_start", stage="parse")
            if path:
                raw_config = load_json_config(path)
            elif config_dict:
                raw_config = config_dict
            elif workflow_dict:
                # Wrap workflow in minimal config
                raw_config = self._wrap_workflow(workflow_dict)
            else:
                raise ValueError("Either path, config_dict, or workflow_dict must be provided")
            
            # Stage 2: Schema Validation (Gate 1)
            logger.info("compilation_stage_start", stage="schema_validation")
            schema_validator = SchemaValidator(self.schema_path)
            schema_errors = schema_validator.validate_json_schema(raw_config)
            if schema_errors:
                result.errors = schema_errors
                return result
            
            # Stage 3: Pydantic Validation (Gate 2)
            logger.info("compilation_stage_start", stage="pydantic_validation")
            try:
                config = AgenticAIConfig(**raw_config)
            except Exception as e:
                result.errors = [f"Pydantic validation failed: {e}"]
                return result
            
            # Stage 4: Extract workflow
            if workflow_dict:
                workflow = WorkflowSchema(**workflow_dict)
            else:
                workflow = self._extract_workflow(raw_config)
                if not workflow:
                    result.errors = ["No workflow found in configuration"]
                    return result
            
            # Stage 5: Semantic Validation (Gate 3)
            logger.info("compilation_stage_start", stage="semantic_validation")
            semantic_validator = SemanticValidator(config)
            semantic_errors = semantic_validator.validate(workflow)
            if semantic_errors:
                result.errors = semantic_errors
                return result
            
            # Stage 6: Dependency Resolution
            logger.info("compilation_stage_start", stage="dependency_resolution")
            try:
                resolver = DependencyResolver(workflow)
                execution_order = resolver.topological_sort()
            except CycleDetectedError as e:
                result.errors = [f"Cycle detected in workflow: {' -> '.join(e.cycle)}"]
                return result
            except Exception as e:
                result.errors = [f"Dependency resolution failed: {e}"]
                return result
            
            # Stage 7: Graph Building
            logger.info("compilation_stage_start", stage="graph_building")
            try:
                graph_builder = GraphBuilder(
                    config=config,
                    workflow=workflow,
                    checkpointer=None,  # Will be set at runtime
                    store=None,
                )
                graph = graph_builder.build()
            except Exception as e:
                result.errors = [f"Graph building failed: {e}"]
                return result
            
            # Stage 8: Middleware Injection
            logger.info("compilation_stage_start", stage="middleware_injection")
            # Middleware is injected at runtime via GraphBuilder
            
            # Success
            result.success = True
            result.graph = graph
            result.workflow = workflow
            result.config = config
            result.execution_order = execution_order
            result.compilation_time_ms = (time.perf_counter() - start_time) * 1000
            
            logger.info("compilation_success", 
                       workflow=workflow.workflow_id,
                       node_count=len(execution_order),
                       time_ms=result.compilation_time_ms)
            
        except Exception as e:
            logger.error("compilation_failed", error=str(e))
            result.errors = [f"Compilation failed: {e}"]
        
        # Cache result
        if use_cache:
            self._compilation_cache[cache_key] = result
        
        return result
    
    def _compute_cache_key(
        self, 
        path: Optional[Union[str, Path]], 
        config_dict: Optional[Dict[str, Any]], 
        workflow_dict: Optional[Dict[str, Any]]
    ) -> str:
        """Compute cache key for compilation."""
        
        if path:
            content = path.read_bytes() if isinstance(path, Path) else Path(path).read_bytes()
        elif config_dict:
            content = json.dumps(config_dict, sort_keys=True).encode()
        elif workflow_dict:
            content = json.dumps(workflow_dict, sort_keys=True).encode()
        else:
            content = b"empty"
        
        return hashlib.sha256(content).hexdigest()[:16]
    
    def _wrap_workflow(self, workflow_dict: Dict[str, Any]) -> Dict[str, Any]:
        """Wrap workflow in minimal config structure."""
        return {
            "apiVersion": "agenticai/v1",
            "kind": "Config",
            "metadata": {
                "name": workflow_dict.get("workflow_id", "unknown"),
                "version": "1.0.0"
            },
            "platform": {"name": "agenticai", "environment": "development"},
            "integrations": {
                "chat_models": [{"id": "default", "provider": "openai", "model": "gpt-4o", "priority": 1}],
                "tools": [],
                "middleware": [],
                "persistence": {}
            },
            "spec": workflow_dict
        }
    
    def _extract_workflow(self, raw_config: Dict[str, Any]) -> Optional[WorkflowSchema]:
        """Extract workflow from config."""
        # Check for spec field first (new format)
        if "spec" in raw_config:
            return WorkflowSchema(**raw_config["spec"])
        
        # Legacy format - check for workflow fields at root
        workflow_fields = {"workflow_id", "agents", "edges", "entry_point"}
        if any(f in raw_config for f in workflow_fields):
            return WorkflowSchema(**raw_config)
        
        return None
    
    def compile_to_file(
        self,
        path: Union[str, Path],
        output_path: Union[str, Path],
        use_cache: bool = True,
    ) -> CompilationResult:
        """Compile and save graph to file (for debugging)."""
        result = self.compile(path=path, use_cache=use_cache)
        
        if result.success:
            # Save compiled graph metadata (not the graph itself)
            metadata = {
                "workflow_id": result.workflow.workflow_id if result.workflow else "unknown",
                "execution_order": result.execution_order,
                "compilation_time_ms": result.compilation_time_ms,
                "timestamp": time.time(),
            }
            
            with open(output_path, "w") as f:
                json.dump(metadata, f, indent=2)
        
        return result
    
    async def compile_async(
        self,
        path: Optional[Union[str, Path]] = None,
        config_dict: Optional[Dict[str, Any]] = None,
        workflow_dict: Optional[Dict[str, Any]] = None,
        use_cache: bool = True,
    ) -> CompilationResult:
        """Async version of compile."""
        # For now, just delegate to sync version
        return self.compile(path=path, config_dict=config_dict, workflow_dict=workflow_dict, use_cache=use_cache)


def compile_workflow(
    path: Optional[Union[str, Path]] = None,
    config_dict: Optional[Dict[str, Any]] = None,
    workflow_dict: Optional[Dict[str, Any]] = None,
    checkpointer: Optional[Any] = None,
    store: Optional[Any] = None,
    schema_path: Optional[Union[str, Path]] = None,
) -> CompilationResult:
    """Convenience function to compile a workflow."""
    compiler = Compiler(schema_path=schema_path, checkpointer=checkpointer, store=store)
    return compiler.compile(path=path, config_dict=config_dict, workflow_dict=workflow_dict)


async def compile_workflow_async(
    path: Optional[Union[str, Path]] = None,
    config_dict: Optional[Dict[str, Any]] = None,
    workflow_dict: Optional[Dict[str, Any]] = None,
    checkpointer: Optional[Any] = None,
    store: Optional[Any] = None,
    schema_path: Optional[Union[str, Path]] = None,
) -> CompilationResult:
    """Async convenience function to compile a workflow."""
    compiler = Compiler(schema_path=schema_path, checkpointer=checkpointer, store=store)
    return await compiler.compile_async(path=path, config_dict=config_dict, workflow_dict=workflow_dict)