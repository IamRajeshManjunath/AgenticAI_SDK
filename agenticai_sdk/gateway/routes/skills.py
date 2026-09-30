"""FastAPI route handlers for Skills management.

Endpoints:
  GET    /api/v1/skills                    — List all skills (name, description)
  POST   /api/v1/skills                    — Create new skill
  GET    /api/v1/skills/{name}             — Get full skill content
  PUT    /api/v1/skills/{name}             — Update skill
  DELETE /api/v1/skills/{name}             — Delete skill
  POST   /api/v1/skills/{name}/validate    — Validate SKILL.md
  POST   /api/v1/skills/reload             — Trigger hot reload
  POST   /api/v1/skills/sync               — Sync remote sources
  GET    /api/v1/skills/{name}/files       — List supporting files
  POST   /api/v1/skills/{name}/files       — Upload supporting file
"""

from __future__ import annotations

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, File, Form
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import Dict, List, Optional, Any

from agenticai_sdk.auth.permissions import require_permission
from agenticai_sdk.config.schemas import RemoteSkillSource
from agenticai_sdk.db import get_session
from agenticai_sdk.db.models import User
from agenticai_sdk.skills.loader import SkillValidationError
from agenticai_sdk.skills.registry import get_skills_registry
from agenticai_sdk.skills.models import SkillMetadata, SkillSource

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/api/v1/skills", tags=["skills"])


# ── Request/Response Models ──────────────────────────────────────────────────────

class SkillCreateRequest(BaseModel):
    name: str
    frontmatter: Dict[str, Any]
    content: str
    files: Optional[Dict[str, str]] = None

    class Config:
        arbitrary_types_allowed = True


class SkillUpdateRequest(BaseModel):
    frontmatter: Optional[Dict[str, Any]] = None
    content: Optional[str] = None
    files: Optional[Dict[str, str]] = None

    class Config:
        arbitrary_types_allowed = True


class SkillValidateResponse(BaseModel):
    valid: bool
    errors: List[str] = []

    class Config:
        arbitrary_types_allowed = True


class SkillListResponse(BaseModel):
    skills: List[SkillMetadata]

    class Config:
        arbitrary_types_allowed = True


class SkillResponse(BaseModel):
    name: str
    description: str
    frontmatter: Dict[str, Any]
    content: str
    files: Dict[str, str]
    source: SkillSource
    modified_at: str

    class Config:
        arbitrary_types_allowed = True


class ReloadResponse(BaseModel):
    reloaded: List[str]
    failed: List[str]

    class Config:
        arbitrary_types_allowed = True


class SyncResponse(BaseModel):
    synced: List[str]
    failed: List[str]

    class Config:
        arbitrary_types_allowed = True


# ── Helper Functions ────────────────────────────────────────────────────────────

def _get_workspace_id(request: Request) -> str:
    return getattr(request.state, "workspace_id", None) or "default"


def _manifest_to_response(manifest) -> SkillResponse:
    """Convert SkillManifest to API response."""
    return SkillResponse(
        name=manifest.name,
        description=manifest.description,
        frontmatter=manifest.frontmatter.model_dump(),
        content=manifest.content,
        files={f.path: f.content for f in manifest.files},
        source=manifest.source,
        modified_at=manifest.modified_at.isoformat(),
    )


# ── Route Handlers ──────────────────────────────────────────────────────────────

@router.get("", response_model=SkillListResponse)
async def list_skills(
    request: Request,
    db: Session = Depends(get_session),
    _: User = Depends(require_permission("skill:read")),
):
    """List all skills (name + description for system prompt)."""
    registry = get_skills_registry()
    skills = registry.list_skills()
    return SkillListResponse(skills=skills)


@router.post("", response_model=SkillResponse, status_code=201)
async def create_skill(
    request: Request,
    body: SkillCreateRequest,
    db: Session = Depends(get_session),
    _: User = Depends(require_permission("skill:create")),
):
    """Create a new skill directory with SKILL.md and supporting files."""
    registry = get_skills_registry()
    
    try:
        manifest = registry.create_skill(
            name=body.name,
            frontmatter=body.frontmatter,
            content=body.content,
            files=body.files,
        )
    except SkillValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    
    return _manifest_to_response(manifest)


@router.get("/{name}", response_model=SkillResponse)
async def get_skill(
    name: str,
    request: Request,
    db: Session = Depends(get_session),
    _: User = Depends(require_permission("skill:read")),
):
    """Get full skill content including frontmatter, markdown, and supporting files."""
    registry = get_skills_registry()
    manifest = registry.get_skill(name)
    
    if not manifest:
        raise HTTPException(status_code=404, detail=f"Skill '{name}' not found")
    
    return _manifest_to_response(manifest)


@router.put("/{name}", response_model=SkillResponse)
async def update_skill(
    name: str,
    request: Request,
    body: SkillUpdateRequest,
    db: Session = Depends(get_session),
    _: User = Depends(require_permission("skill:update")),
):
    """Update an existing skill's frontmatter, content, or supporting files."""
    registry = get_skills_registry()
    
    if not registry.get_skill(name):
        raise HTTPException(status_code=404, detail=f"Skill '{name}' not found")
    
    try:
        manifest = registry.update_skill(
            name=name,
            frontmatter=body.frontmatter,
            content=body.content,
            files=body.files,
        )
    except SkillValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    
    return _manifest_to_response(manifest)


@router.delete("/{name}")
async def delete_skill(
    name: str,
    request: Request,
    db: Session = Depends(get_session),
    _: User = Depends(require_permission("skill:delete")),
):
    """Delete a skill directory."""
    registry = get_skills_registry()
    
    if not registry.get_skill(name):
        raise HTTPException(status_code=404, detail=f"Skill '{name}' not found")
    
    registry.delete_skill(name)
    return {"success": True, "message": f"Skill '{name}' deleted"}


@router.post("/{name}/validate", response_model=SkillValidateResponse)
async def validate_skill(
    name: str,
    request: Request,
    db: Session = Depends(get_session),
    _: User = Depends(require_permission("skill:read")),
):
    """Validate a skill against the Agent Skills specification."""
    registry = get_skills_registry()
    errors = registry.validate_skill(name)
    
    return SkillValidateResponse(
        valid=len(errors) == 0,
        errors=errors,
    )


@router.post("/reload", response_model=ReloadResponse)
async def reload_skills(
    request: Request,
    db: Session = Depends(get_session),
    _: User = Depends(require_permission("skill:update")),
):
    """Trigger hot reload of all skills from disk."""
    registry = get_skills_registry()
    
    # Trigger full refresh
    skills = registry.refresh()
    
    return ReloadResponse(
        reloaded=[s.name for s in skills],
        failed=[],
    )


@router.post("/sync", response_model=SyncResponse)
async def sync_skills(
    request: Request,
    db: Session = Depends(get_session),
    _: User = Depends(require_permission("skill:sync")),
):
    """Sync remote skill sources (git, S3, Fleet)."""
    registry = get_skills_registry()
    
    try:
        new_skills = await registry.sync_remotes()
        return SyncResponse(
            synced=[s.name for s in new_skills],
            failed=[],
        )
    except Exception as exc:
        logger.error("skills_sync_failed", error=str(exc))
        return SyncResponse(synced=[], failed=[str(exc)])


@router.post("/{name}/files")
async def upload_skill_file(
    name: str,
    request: Request,
    file: UploadFile = File(...),
    path: str = Form(...),
    db: Session = Depends(get_session),
    _: User = Depends(require_permission("skill:upload")),
):
    """Upload a supporting file to a skill directory."""
    registry = get_skills_registry()
    
    if not registry.get_skill(name):
        raise HTTPException(status_code=404, detail=f"Skill '{name}' not found")
    
    # Read file content
    content = await file.read()
    try:
        text_content = content.decode("utf-8")
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="Only text files are supported")
    
    # Update skill with new file
    try:
        manifest = registry.update_skill(
            name=name,
            files={path: text_content},
        )
    except SkillValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    
    return {"success": True, "file": path}


@router.get("/{name}/files")
async def list_skill_files(
    name: str,
    request: Request,
    db: Session = Depends(get_session),
    _: User = Depends(require_permission("skill:read")),
):
    """List all supporting files for a skill."""
    registry = get_skills_registry()
    manifest = registry.get_skill(name)
    
    if not manifest:
        raise HTTPException(status_code=404, detail=f"Skill '{name}' not found")
    
    files = []
    for f in manifest.files:
        files.append({
            "path": f.path,
            "type": f.type.value,
            "size_bytes": f.size_bytes,
        })
    
    return {"files": files}


# Rebuild models to resolve forward references
SkillCreateRequest.model_rebuild()
SkillUpdateRequest.model_rebuild()
SkillValidateResponse.model_rebuild()
SkillListResponse.model_rebuild()
SkillResponse.model_rebuild()
ReloadResponse.model_rebuild()
SyncResponse.model_rebuild()