from sqlalchemy import Column, Integer, String, JSON, DateTime, ForeignKey, Float
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from .database import Base

class Workspace(Base):
    __tablename__ = "workspaces"

    id = Column(String, primary_key=True, index=True)
    name = Column(String, index=True)
    description = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    workflows = relationship("Workflow", back_populates="workspace", cascade="all, delete-orphan")

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
    name = Column(String, index=True)
    description = Column(String, nullable=True)
    tool_type = Column(String) # 'mcp', 'custom_python', 'system'
    code_or_url = Column(String)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

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

