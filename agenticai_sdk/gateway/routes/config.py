"""FastAPI route handlers for configuration management.

Endpoints:
  GET    /api/v1/config              — Get current configuration
  PUT    /api/v1/config              — Update configuration (JSON Merge Patch)
  POST   /api/v1/config/reload       — Force reload configuration
  GET    /api/v1/config/stream       — SSE stream for config changes
  GET    /api/v1/config/schema       — Get JSON schema for config validation
"""

from __future__ import annotations

import asyncio
import json
from typing import Any, Dict, Optional

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from agenticai_sdk.auth.permissions import require_permission
from agenticai_sdk.config.loader import get_config_loader, load_config_async
from agenticai_sdk.config.manager import ConfigurationManager
from agenticai_sdk.config.schemas import AgenticAIConfig
from agenticai_sdk.db import get_session
from agenticai_sdk.db.models import User

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/v1/config", tags=["config"])


class ConfigUpdateRequest(BaseModel):
    """Request model for config updates."""
    config: Dict[str, Any]
    merge_strategy: str = "id_aware"  # "json_merge", "id_aware", "replace"


class ConfigReloadRequest(BaseModel):
    """Request model for config reload."""
    force: bool = False


class ConfigResponse(BaseModel):
    """Response model for config."""
    platform: Dict[str, Any]
    integrations: Dict[str, Any]
    version: str
    last_modified: Optional[str] = None


def _get_config_path(request: Request) -> str:
    """Get config path from request state or default."""
    return getattr(request.state, "config_path", "agenticai.yaml")


def _get_workspace_id(request: Request) -> str:
    """Get workspace ID from request state."""
    return getattr(request.state, "workspace_id", "default")


@router.get("", response_model=ConfigResponse)
async def get_config(
    request: Request,
    _: User = Depends(require_permission("config:read")),
):
    """Get current configuration."""
    loader = get_config_loader()
    config = loader.get_config()
    
    config_dict = config.model_dump()
    config_manager = ConfigurationManager(_get_config_path(request))
    version = config_manager.get_config_hash() or "unknown"
    
    return ConfigResponse(
        platform=config_dict.get("platform", {}),
        integrations=config_dict.get("integrations", {}),
        version=version,
        last_modified=None,  # Could add file mtime
    )


@router.get("/schema")
async def get_config_schema(
    request: Request,
    _: User = Depends(require_permission("config:read")),
):
    """Get JSON schema for configuration validation."""
    schema = AgenticAIConfig.model_json_schema()
    return schema


@router.put("", response_model=ConfigResponse)
async def update_config(
    request: Request,
    body: ConfigUpdateRequest,
    _: User = Depends(require_permission("config:update")),
):
    """Update configuration with JSON Merge Patch.
    
    Supports three merge strategies:
    - "id_aware": Merge lists by 'id' field (default, best for chat_models, tools, etc.)
    - "json_merge": RFC 7396 JSON Merge Patch (null deletes keys)
    - "replace": Simple dict replacement
    """
    config_path = _get_config_path(request)
    config_manager = ConfigurationManager(config_path)
    
    try:
        updated = config_manager.validate_and_save(
            body.config,
            merge_strategy=body.merge_strategy
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logger.error("config_update_failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"Configuration update failed: {str(e)}")
    
    # Notify config loader to reload
    loader = get_config_loader()
    await loader.reload_async()
    
    return ConfigResponse(
        platform=updated.get("platform", {}),
        integrations=updated.get("integrations", {}),
        version=config_manager.get_config_hash() or "unknown",
    )


@router.post("/reload", response_model=ConfigResponse)
async def reload_config(
    request: Request,
    body: ConfigReloadRequest,
    _: User = Depends(require_permission("config:update")),
):
    """Force reload configuration from disk."""
    loader = get_config_loader()
    config = await loader.reload_async()
    
    config_dict = config.model_dump()
    config_manager = ConfigurationManager(_get_config_path(request))
    
    return ConfigResponse(
        platform=config_dict.get("platform", {}),
        integrations=config_dict.get("integrations", {}),
        version=config_manager.get_config_hash() or "unknown",
    )


@router.get("/stream")
async def stream_config_changes(
    request: Request,
    token: Optional[str] = Query(None),
    _: User = Depends(require_permission("config:read")),
):
    """SSE endpoint for real-time config change notifications.
    
    Authenticate via query parameter token (for EventSource compatibility).
    """
    # Validate token if provided (for EventSource which can't send headers)
    if token:
        # In production, validate token here
        pass
    
    loader = get_config_loader()
    queue: asyncio.Queue = asyncio.Queue()
    
    async def on_config_change(config: AgenticAIConfig):
        await queue.put({
            "type": "config_updated",
            "data": config.model_dump(),
            "version": ConfigurationManager(_get_config_path(request)).get_config_hash(),
        })
    
    loader.on_change(on_config_change)
    
    async def event_generator():
        try:
            # Send initial config
            initial_config = loader.get_config()
            yield {
                "event": "config_updated",
                "data": json.dumps({
                    "type": "initial",
                    "data": initial_config.model_dump(),
                    "version": ConfigurationManager(_get_config_path(request)).get_config_hash(),
                })
            }
            
            while True:
                event = await queue.get()
                yield {
                    "event": event["type"],
                    "data": json.dumps(event)
                }
        except asyncio.CancelledError:
            loader.remove_change_callback(on_config_change)
            raise
        except Exception as e:
            logger.error("config_stream_error", error=str(e))
            loader.remove_change_callback(on_config_change)
            raise
    
    return EventSourceResponse(event_generator())