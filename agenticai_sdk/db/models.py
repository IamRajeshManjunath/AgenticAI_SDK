from sqlalchemy import Column, Integer, String, JSON, DateTime, ForeignKey, Float, Boolean
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from .database import Base


class Plan(Base):
    __tablename__ = "plans"

    id = Column(String, primary_key=True, index=True)
    name = Column(String, nullable=False)
    stripe_price_id = Column(String, nullable=True)
    tokens_per_month = Column(Integer, default=100000)
    max_workflows = Column(Integer, default=5)
    max_api_keys = Column(Integer, default=2)
    max_team_members = Column(Integer, default=1)
    features = Column(JSON, default=dict)
    price_cents = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String, nullable=True)
    is_active = Column(Integer, default=1)
    is_superuser = Column(Integer, default=0)
    default_workspace_id = Column(String, ForeignKey("workspaces.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class WorkspaceMember(Base):
    __tablename__ = "workspace_members"

    workspace_id = Column(String, ForeignKey("workspaces.id", ondelete="CASCADE"), primary_key=True)
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    role = Column(String, nullable=False, default="editor")  # admin | editor | viewer
    invited_by = Column(String, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    workspace = relationship("Workspace", backref="members")
    user = relationship("User", backref="memberships", foreign_keys=[user_id])


class ApiKey(Base):
    __tablename__ = "api_keys"

    id = Column(String, primary_key=True, index=True)
    workspace_id = Column(String, ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False)
    workflow_id = Column(String, ForeignKey("workflows.id", ondelete="CASCADE"), nullable=True, index=True)
    key_prefix = Column(String, nullable=False)
    key_hash = Column(String, nullable=False)
    name = Column(String, nullable=False)
    is_active = Column(Integer, default=1)
    last_used_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    workspace = relationship("Workspace", backref="api_keys")
    workflow = relationship("Workflow", backref="api_keys")


class Workspace(Base):
    __tablename__ = "workspaces"

    id = Column(String, primary_key=True, index=True)
    name = Column(String, index=True)
    description = Column(String, nullable=True)
    owner_id = Column(String, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    plan_id = Column(String, ForeignKey("plans.id", ondelete="SET NULL"), nullable=True)
    stripe_customer_id = Column(String, nullable=True)
    stripe_subscription_id = Column(String, nullable=True)
    subscription_status = Column(String, default="inactive")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    workflows = relationship("Workflow", back_populates="workspace", cascade="all, delete-orphan")
    owner = relationship("User", backref="owned_workspaces", foreign_keys=[owner_id])
    plan = relationship("Plan", backref="workspaces")

class Workflow(Base):
    __tablename__ = "workflows"

    id = Column(String, primary_key=True, index=True)
    workspace_id = Column(String, ForeignKey("workspaces.id", ondelete="CASCADE"))
    name = Column(String, index=True)
    description = Column(String, nullable=True)
    config = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    workspace = relationship("Workspace", back_populates="workflows")

class Tool(Base):
    __tablename__ = "tools"

    id = Column(String, primary_key=True, index=True)
    workspace_id = Column(String, ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=True)
    name = Column(String, index=True)
    description = Column(String, nullable=True)
    tool_type = Column(String) # 'mcp', 'custom_python', 'system'
    code_or_url = Column(String)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    workspace = relationship("Workspace", backref="tools")

class ActivityLog(Base):
    __tablename__ = "activity_logs"

    id = Column(String, primary_key=True, index=True)
    workspace_id = Column(String, index=True, nullable=True)
    workflow_id = Column(String, index=True, nullable=True)
    event_type = Column(String)
    details = Column(JSON)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class WorkflowTrace(Base):
    """Deep observability mapping for executed workflow traces."""
    __tablename__ = "workflow_traces"

    id = Column(String, primary_key=True, index=True)
    workflow_id = Column(String, ForeignKey("workflows.id", ondelete="CASCADE"), index=True)
    trace_id = Column(String, index=True)
    duration_ms = Column(Float)
    total_tokens = Column(Integer)
    cost_usd = Column(Float)
    error_count = Column(Integer)
    span_tree = Column(JSON) # Serialized full trace tree
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    workflow = relationship("Workflow")

class SchemaAuditTrail(Base):
    """Immutable audit trail recording exact node payloads and schema enforcement actions."""
    __tablename__ = "schema_audit_trails"

    id = Column(String, primary_key=True, index=True)
    agent_id = Column(String, index=True)
    direction = Column(String)  # 'incoming' or 'outgoing'
    payload = Column(JSON)      # The exact data
    schema_definition = Column(JSON) # The schema it was validated against
    is_valid = Column(Integer)  # 1 for valid, 0 for violation
    violation_error = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class BillingData(Base):
    __tablename__ = "billing_data"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    workspace_id = Column(String, index=True)
    amount = Column(Float)
    currency = Column(String, default="USD")
    period_start = Column(DateTime(timezone=True))
    period_end = Column(DateTime(timezone=True))
    metrics = Column(JSON) # e.g. token usage
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class CronJob(Base):
    __tablename__ = "cron_jobs"

    id = Column(String, primary_key=True, index=True)
    cron_expression = Column(String, nullable=False) # e.g. "*/5 * * * *"
    target_type = Column(String, nullable=False)     # "agent" | "workflow"
    target_id = Column(String, nullable=False)       # The workflow_id or agent_id
    payload = Column(JSON, nullable=True)            # Execution state input
    last_run_at = Column(DateTime(timezone=True), nullable=True)
    next_run_at = Column(DateTime(timezone=True), index=True, nullable=False)
    status = Column(String, default="active")        # "active" | "paused" | "terminated"
    locked_by = Column(String, nullable=True)        # Active instance name
    locked_until = Column(DateTime(timezone=True), nullable=True) # Lock lease duration
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class RAGSource(Base):
    __tablename__ = "rag_sources"

    id = Column(String, primary_key=True, index=True)
    workspace_id = Column(String, ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=True)
    name = Column(String, index=True)
    provider = Column(String, default="qdrant")
    config = Column(JSON, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    workspace = relationship("Workspace", backref="rag_sources")


class IntegrationConnection(Base):
    __tablename__ = "integration_connections"

    id = Column(String, primary_key=True, index=True) # e.g. "workspace_id:slack"
    workspace_id = Column(String, index=True, nullable=False)
    integration_type = Column(String, nullable=False) # "slack", "outlook", "teams", "whatsapp"
    name = Column(String, nullable=False)
    auth_state = Column(JSON, nullable=False)         # { access_token, webhook_url, etc }
    rate_limits = Column(JSON, nullable=True)         # { max_calls_per_minute }
    is_active = Column(Integer, default=1)            # 1 for active, 0 for inactive
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class Secret(Base):
    """Encrypted secret storage — values are Fernet-encrypted at rest and
    decrypted on-demand for users with ``secret:read-value`` permission."""
    __tablename__ = "secrets"

    id = Column(String, primary_key=True, index=True)
    workspace_id = Column(String, ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String, index=True, nullable=False)
    encrypted_value = Column(String, nullable=False)
    description = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    workspace = relationship("Workspace", backref="secrets")


class Policy(Base):
    """IAM policy document — analogous to an AWS IAM policy.

    Attached to principals (users, roles, workspaces) via PolicyAttachment.
    """

    __tablename__ = "policies"

    id = Column(String, primary_key=True, index=True)
    name = Column(String, nullable=False)
    description = Column(String, nullable=True)
    policy_document = Column(JSON, nullable=False)     # {"version":"1","statements":[...]}
    is_system = Column(Integer, default=0)             # System policies cannot be deleted
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class PolicyAttachment(Base):
    """Binds a Policy to a principal (user, role, or workspace)."""

    __tablename__ = "policy_attachments"

    id = Column(String, primary_key=True, index=True)
    policy_id = Column(String, ForeignKey("policies.id", ondelete="CASCADE"), nullable=False, index=True)
    principal_type = Column(String, nullable=False, index=True)   # "user" | "role" | "workspace"
    principal_id = Column(String, nullable=False, index=True)     # user UUID | role name | workspace UUID
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    policy = relationship("Policy", backref="attachments")

