"""Middleware registry for AgenticAI SDK."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from agenticai_sdk.plugins import get_global_registry, IntegrationType

import structlog

logger = structlog.get_logger(__name__)


class MiddlewareRegistry:
    """Registry for middleware providers."""
    
    def __init__(self, registry=None):
        self._registry = registry or get_global_registry()
        self._builtin_middleware = {
            "rate_limiter": "agenticai_sdk.middleware.rate_limiter.RateLimiterMiddleware",
            "pii_masking": "agenticai_sdk.middleware.pii_masking.PIIMaskingMiddleware",
            "prompt_injection_firewall": "agenticai_sdk.middleware.prompt_injection_firewall.PromptInjectionFirewallMiddleware",
            "schema_validation": "agenticai_sdk.middleware.schema_validation.SchemaValidationMiddleware",
            "schema_audit": "agenticai_sdk.middleware.schema_audit.SchemaAuditMiddleware",
            "context_compression": "agenticai_sdk.middleware.context_compression.ContextCompressionMiddleware",
            "budget_guardrails": "agenticai_sdk.middleware.budget_guardrails.BudgetGuardrailsMiddleware",
            "prometheus_metrics": "agenticai_sdk.middleware.prometheus_metrics.PrometheusMetricsMiddleware",
        }
    
    def create_middleware(self, config: Dict[str, Any]) -> Any:
        """Create middleware instance from config."""
        mw_type = config.get("type")
        if not mw_type:
            raise ValueError("Middleware config must include 'type'")
        
        # Try plugin registry first
        plugin = self._registry.get_plugin(IntegrationType.MIDDLEWARE, mw_type)
        if plugin:
            return plugin.create_instance(config)
        
        # Try built-in middleware
        if mw_type in self._builtin_middleware:
            import importlib
            module_path, class_name = self._builtin_middleware[mw_type].rsplit(".", 1)
            module = importlib.import_module(module_path)
            middleware_class = getattr(module, class_name)
            return middleware_class(**config.get("config", {}))
        
        raise ValueError(f"Unknown middleware type: {mw_type}")
    
    def create_from_configs(self, middleware_configs: List[Dict[str, Any]]) -> List[Any]:
        """Create multiple middleware instances."""
        return [self.create_middleware(cfg) for cfg in middleware_configs if cfg.get("enabled", True)]
    
    def list_available(self) -> List[Dict[str, Any]]:
        """List available middleware types."""
        builtin = [
            {
                "type": k,
                "name": k.replace("_", " ").title(),
                "source": "builtin",
            }
            for k in self._builtin_middleware.keys()
        ]
        
        plugins = self._registry.list_available(IntegrationType.MIDDLEWARE)
        plugin_list = [
            {
                "type": p.provider,
                "name": p.name,
                "description": p.description,
                "package": p.package_name,
                "version": p.version,
                "source": "plugin",
            }
            for p in plugins
        ]
        
        return builtin + plugin_list


class MiddlewarePipelineBuilder:
    """Builds middleware pipeline from configuration."""
    
    def __init__(self, registry=None):
        self.registry = MiddlewareRegistry(registry)
        self._middleware: List[Any] = []
    
    def add_builtin(self, mw_type: str, config: Dict[str, Any] = None) -> "MiddlewarePipelineBuilder":
        """Add built-in middleware."""
        config = config or {}
        config["type"] = mw_type
        mw = self.registry.create_middleware(config)
        self._middleware.append(mw)
        return self
    
    def add_plugin(self, provider: str, config: Dict[str, Any]) -> "MiddlewarePipelineBuilder":
        """Add plugin middleware."""
        config = config.copy()
        config["type"] = provider
        mw = self.registry.create_middleware(config)
        self._middleware.append(mw)
        return self
    
    def add_from_config(self, config: Dict[str, Any]) -> "MiddlewarePipelineBuilder":
        """Add middleware from config dict."""
        mw = self.registry.create_middleware(config)
        self._middleware.append(mw)
        return self
    
    def add_from_configs(self, configs: List[Dict[str, Any]]) -> "MiddlewarePipelineBuilder":
        """Add multiple middleware from configs."""
        for config in configs:
            if config.get("enabled", True):
                self.add_from_config(config)
        return self
    
    def build(self) -> List[Any]:
        """Build and return the middleware pipeline."""
        return self._middleware


def create_default_pipeline() -> List[Any]:
    """Create default middleware pipeline."""
    builder = MiddlewarePipelineBuilder()
    return (
        builder
        .add_builtin("rate_limiter", {"config": {"requests_per_minute": 60}})
        .add_builtin("pii_masking")
        .add_builtin("prompt_injection_firewall")
        .add_builtin("schema_validation")
        .add_builtin("budget_guardrails")
        .add_builtin("prometheus_metrics")
        .build()
    )