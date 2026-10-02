from sqlalchemy import Column, Integer, String, JSON, DateTime, ForeignKey, Float, Boolean, Enum, UniqueConstraint, BigInteger, Text
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from .database import Base
from agenticai_sdk.config.schemas import DatabasePurpose


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
    organization_id = Column(String, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=True, index=True, default="default-org")
    name = Column(String, index=True)
    description = Column(String, nullable=True)
    owner_id = Column(String, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    plan_id = Column(String, ForeignKey("plans.id", ondelete="SET NULL"), nullable=True)
    stripe_customer_id = Column(String, nullable=True)
    stripe_subscription_id = Column(String, nullable=True)
    subscription_status = Column(String, default="inactive")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    organization = relationship("Organization", backref="workspaces")
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
    revisions = relationship("WorkflowRevision", back_populates="workflow", cascade="all, delete-orphan")

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
    """General activity logging for debugging and operational visibility.
    
    Contains PII and may be redacted in telemetry exports.
    """
    __tablename__ = "activity_logs"

    id = Column(String, primary_key=True, index=True)
    workspace_id = Column(String, index=True, nullable=True)
    workflow_id = Column(String, index=True, nullable=True)
    event_type = Column(String)
    details = Column(JSON)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class AuditLog(Base):
    """Immutable security audit log for compliance and forensics.
    
    Contains security-relevant events with full fidelity.
    Never redacted - contains full PII/secrets for forensic analysis.
    Retention governed by compliance policies.
    """
    __tablename__ = "audit_logs"

    id = Column(String, primary_key=True, index=True)
    workspace_id = Column(String, index=True, nullable=False)
    user_id = Column(String, index=True, nullable=True)  # Actor who performed action
    
    # Event classification
    event_category = Column(String, nullable=False, index=True)  # auth, data, config, admin, security
    event_type = Column(String, nullable=False, index=True)      # login, logout, create, delete, permission_change, etc.
    severity = Column(String, default="info", index=True)        # info, warning, critical
    
    # Resource affected
    resource_type = Column(String, index=True, nullable=True)    # workflow, secret, policy, user, workspace
    resource_id = Column(String, index=True, nullable=True)
    resource_name = Column(String, nullable=True)
    
    # Action details (full fidelity - no redaction)
    action = Column(String, nullable=False)                      # create, read, update, delete, execute, grant, revoke
    outcome = Column(String, nullable=False, index=True)         # success, failure, denied
    details = Column(JSON, nullable=False)                       # Full context - NO REDACTION
    
    # Request context
    ip_address = Column(String, nullable=True)
    user_agent = Column(String, nullable=True)
    request_id = Column(String, index=True, nullable=True)
    
    # Session context
    session_id = Column(String, index=True, nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)

class WorkflowTrace(Base):
    """Deep observability mapping for executed workflow traces."""
    __tablename__ = "workflow_traces"

    id = Column(String, primary_key=True, index=True)
    workflow_id = Column(String, ForeignKey("workflows.id", ondelete="CASCADE"), index=True)
    workspace_id = Column(String, index=True, nullable=True)
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


class DatabaseRoute(Base):
    """User-configured database connections for external stores with strict purpose-bound schema."""
    __tablename__ = "database_routes"
    
    id = Column(String, primary_key=True, index=True)
    workspace_id = Column(String, ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Route identification
    name = Column(String, nullable=False)
    purpose = Column(Enum(DatabasePurpose), nullable=False, index=True)
    provider = Column(String, nullable=False)
    
    # Connection config (non-sensitive)
    config = Column(JSON, nullable=False)
    
    # SCHEMA CONTRACT - VALIDATED AT CREATION, ENFORCED AT RUNTIME
    schema_contract = Column(JSON, nullable=False)
    schema_version = Column(String, default="1.0")
    schema_hash = Column(String, nullable=False)
    
    # Sensitive config (encrypted)
    config_encrypted = Column(JSON, nullable=True)
    
    # Health & enforcement
    is_active = Column(Integer, default=1)
    last_schema_validation = Column(DateTime(timezone=True), nullable=True)
    schema_validation_status = Column(String, default="pending")
    last_health_check = Column(DateTime(timezone=True), nullable=True)
    health_status = Column(String, default="unknown")
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # CONSTRAINT: One route per purpose per workspace
    __table_args__ = (
        UniqueConstraint('workspace_id', 'purpose', name='uq_workspace_purpose'),
    )
    
    workspace = relationship("Workspace", backref="database_routes")


class IntegrationCredential(Base):
    """Encrypted credentials for integration providers."""
    __tablename__ = "integration_credentials"
    
    id = Column(String, primary_key=True, index=True)
    workspace_id = Column(String, ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True)
    
    integration_type = Column(String, nullable=False)
    provider = Column(String, nullable=False)
    name = Column(String, nullable=False)
    
    # Encrypted credential payload
    credential_type = Column(String, nullable=False)
    encrypted_payload = Column(String, nullable=False)
    
    # Alias for backwards compatibility with tests
    @property
    def credentials_encrypted(self):
        return self.encrypted_payload
    
    @credentials_encrypted.setter
    def credentials_encrypted(self, value):
        self.encrypted_payload = value
    
    # Metadata
    is_active = Column(Integer, default=1)
    last_validated = Column(DateTime(timezone=True), nullable=True)
    validation_status = Column(String, default="pending")
    created_by = Column(String, ForeignKey("users.id", ondelete="SET NULL"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    workspace = relationship("Workspace", backref="integration_credentials")


class GovernanceEvent(Base):
    """Immutable audit trail for compliance."""
    __tablename__ = "governance_events"
    
    id = Column(String, primary_key=True, index=True)
    workspace_id = Column(String, index=True, nullable=False)
    user_id = Column(String, index=True, nullable=True)
    
    event_category = Column(String, nullable=False)
    event_type = Column(String, nullable=False)
    severity = Column(String, default="info")
    
    resource_type = Column(String, nullable=True)
    resource_id = Column(String, nullable=True)
    
    details = Column(JSON, nullable=True)
    ip_address = Column(String, nullable=True)
    user_agent = Column(String, nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)


class CompliancePolicy(Base):
    """Data retention, access control, encryption policies."""
    __tablename__ = "compliance_policies"
    
    id = Column(String, primary_key=True, index=True)
    workspace_id = Column(String, ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False)
    
    policy_type = Column(String, nullable=False)
    config = Column(JSON, nullable=False)
    is_active = Column(Integer, default=1)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    workspace = relationship("Workspace", backref="compliance_policies")


class Organization(Base):
    """Top-level tenant grouping for multi-tenancy."""
    __tablename__ = "organizations"
    
    id = Column(String, primary_key=True, index=True)
    name = Column(String, nullable=False)
    description = Column(String, nullable=True)
    settings = Column(JSON, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class WorkflowRevision(Base):
    """Immutable workflow configuration revision for versioned deployments."""
    __tablename__ = "workflow_revisions"
    
    id = Column(String, primary_key=True, index=True)
    workflow_id = Column(String, ForeignKey("workflows.id", ondelete="CASCADE"), nullable=False, index=True)
    revision = Column(BigInteger, nullable=False)
    document = Column(JSON, nullable=False)
    content_hash = Column(String, nullable=False)
    status = Column(String, nullable=False)  # draft, validated, published, archived
    created_by = Column(String, ForeignKey("users.id", ondelete="SET NULL"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    workflow = relationship("Workflow", back_populates="revisions")
    creator = relationship("User", backref="created_revisions")
    
    __table_args__ = (
        UniqueConstraint('workflow_id', 'revision', name='uq_workflow_revision'),
        UniqueConstraint('workflow_id', 'content_hash', name='uq_workflow_content_hash'),
    )


class WorkflowRun(Base):
    """Execution run record referencing immutable workflow revision."""
    __tablename__ = "workflow_runs"
    
    id = Column(String, primary_key=True, index=True)
    workspace_id = Column(String, ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True)
    workflow_id = Column(String, ForeignKey("workflows.id", ondelete="CASCADE"), nullable=False, index=True)
    workflow_revision_id = Column(String, ForeignKey("workflow_revisions.id", ondelete="RESTRICT"), nullable=False, index=True)
    status = Column(String, nullable=False)  # pending, running, completed, failed, paused, waiting_approval
    idempotency_key = Column(String, unique=True, index=True, nullable=True)
    input = Column(JSON, nullable=True)
    output = Column(JSON, nullable=True)
    total_input_tokens = Column(BigInteger, default=0)
    total_output_tokens = Column(BigInteger, default=0)
    total_cost_usd = Column(Float, default=0.0)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    workflow = relationship("Workflow", backref="runs")
    workspace = relationship("Workspace", backref="runs")
    workflow_revision = relationship("WorkflowRevision", backref="runs")
    
    __table_args__ = (
        UniqueConstraint('workspace_id', 'idempotency_key', name='uq_workspace_idempotency_key'),
    )

