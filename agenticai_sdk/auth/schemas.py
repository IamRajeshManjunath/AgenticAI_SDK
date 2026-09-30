from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class RegisterRequest(BaseModel):
    email: str = Field(..., min_length=5, max_length=255)
    password: str = Field(..., min_length=8, max_length=128)
    full_name: str = Field(default="", max_length=255)
    workspace_name: str = Field(default="My Workspace", max_length=255)


class LoginRequest(BaseModel):
    email: str = Field(..., min_length=5, max_length=255)
    password: str = Field(..., min_length=1)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: "UserResponse"


class UserResponse(BaseModel):
    id: str
    email: str
    full_name: str
    is_active: bool
    default_workspace_id: Optional[str] = None

    model_config = {"from_attributes": True}


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=8, max_length=128)


class ApiKeyCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    scopes: list[str] = Field(default_factory=list, description="Integration scopes (e.g., 'integration:openai', 'tool:tavily', 'vector:qdrant')")
    workflow_id: Optional[str] = Field(default=None, description="Optional workflow-scoped API key")


class ApiKeyCreateResponse(BaseModel):
    id: str
    name: str
    key: str
    key_prefix: str
    scopes: list[str] = Field(default_factory=list)
    workflow_id: Optional[str] = None


class ApiKeyResponse(BaseModel):
    id: str
    name: str
    key_prefix: str
    is_active: bool
    last_used_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    scopes: list[str] = Field(default_factory=list)
    workflow_id: Optional[str] = None

    model_config = {"from_attributes": True}


class WorkspaceMemberResponse(BaseModel):
    user_id: str
    email: str
    full_name: str
    role: str

    model_config = {"from_attributes": True}


class InviteMemberRequest(BaseModel):
    email: str
    role: str = Field(default="editor", pattern="^(admin|editor|viewer)$")


class UpdateMemberRoleRequest(BaseModel):
    role: str = Field(..., pattern="^(admin|editor|viewer)$")
