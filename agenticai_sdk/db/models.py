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
