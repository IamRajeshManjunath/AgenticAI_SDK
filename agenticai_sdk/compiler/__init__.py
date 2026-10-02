"""Compiler package - Workflow compilation pipeline.

Pipeline stages:
1. Parser - JSON -> Pydantic models
2. Schema Validator - JSON Schema + Pydantic validation
3. Semantic Validator - Deep semantic checks
4. Dependency Resolver - Topological sort, cycle detection
5. Graph Builder - LangGraph StateGraph construction
6. Middleware Injector - Lifecycle-aware middleware injection
"""

from __future__ import annotations

from .parser import (
    parse_config_file,
    parse_config_dict,
    parse_to_pydantic,
    parse_workflow_schema,
    load_and_validate,
    ParseError,
    ValidationError,
)

from .schema_validator import (
    SchemaValidator,
    SchemaValidationError,
    validate_json_schema,
    validate_pydantic,
    validate_all,
)

from .semantic_validator import (
    SemanticValidator,
    SemanticValidationError,
    validate_workflow,
)

from .dependency_resolver import (
    DependencyResolver,
    CycleDetectedError,
    resolve_dependencies,
    topological_sort,
    get_execution_levels,
)

from .graph_builder import (
    GraphBuilder,
    GraphBuildError,
    build_graph,
    compile_workflow,
)

from .middleware_injector import (
    MiddlewareInjector,
    AuthorizationMiddleware,
    PIIDetectionMiddleware,
    InjectionDetectionMiddleware,
    BudgetPrecheckMiddleware,
    ContextManagementMiddleware,
    OutputValidationMiddleware,
    CostAccountingMiddleware,
    PIIRestorationMiddleware,
    TelemetryMiddleware,
    InjectionDetectedError,
    BudgetExceededError,
)

from .compiler import (
    Compiler,
    CompilationResult,
    compile_workflow,
    compile_workflow_async,
)

__all__ = [
    # Parser
    "parse_config_file",
    "parse_config_dict",
    "parse_to_pydantic",
    "parse_workflow_schema",
    "load_and_validate",
    "ParseError",
    "ValidationError",
    
    # Schema Validator
    "SchemaValidator",
    "SchemaValidationError",
    "validate_json_schema",
    "validate_pydantic",
    "validate_all",
    
    # Semantic Validator
    "SemanticValidator",
    "SemanticValidationError",
    "validate_workflow",
    
    # Dependency Resolver
    "DependencyResolver",
    "CycleDetectedError",
    "resolve_dependencies",
    "topological_sort",
    "get_execution_levels",
    
    # Graph Builder
    "GraphBuilder",
    "GraphBuildError",
    "build_graph",
    "compile_workflow",
    
    # Middleware Injector
    "MiddlewareInjector",
    "AuthorizationMiddleware",
    "PIIDetectionMiddleware",
    "InjectionDetectionMiddleware",
    "BudgetPrecheckMiddleware",
    "ContextManagementMiddleware",
    "OutputValidationMiddleware",
    "CostAccountingMiddleware",
    "PIIRestorationMiddleware",
    "TelemetryMiddleware",
    "InjectionDetectedError",
    "BudgetExceededError",
    
    # Compiler
    "Compiler",
    "CompilationResult",
    "compile_workflow",
    "compile_workflow_async",
]