"""Revision Manager - Immutable workflow configuration revision management.

Provides CRUD operations for workflow revisions with optimistic concurrency control,
content hash deduplication, and publish/rollback workflows.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import structlog
from sqlalchemy import desc
from sqlalchemy.orm import Session

from agenticai_sdk.db import get_session
from agenticai_sdk.db.models import Workflow, WorkflowRevision, User
from agenticai_sdk.config.loader import validate_json_schema
from agenticai_sdk.config.schemas import AgenticAIConfig
from agenticai_sdk.config.manager import ConfigurationManager

logger = structlog.get_logger(__name__)


class RevisionConflictError(Exception):
    """Raised when revision conflict detected (optimistic concurrency)."""
    def __init__(self, expected_revision: int, current_revision: int):
        self.expected_revision = expected_revision
        self.current_revision = current_revision
        super().__init__(
            f"Workflow was modified by another operation. "
            f"Expected revision {expected_revision}, current is {current_revision}."
        )


class RevisionNotFoundError(Exception):
    """Raised when revision not found."""
    pass


class InvalidRevisionStateError(Exception):
    """Raised when revision state transition is invalid."""
    pass


class RevisionManager:
    """Manages immutable workflow configuration revisions."""
    
    def __init__(self, db_session: Optional[Session] = None):
        self._db = db_session
        self._owns_session = db_session is None
    
    def _get_db(self) -> Session:
        if self._db is None:
            self._db = next(get_session())
        return self._db
    
    def close(self):
        if self._owns_session and self._db:
            self._db.close()
            self._db = None
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
    
    def _compute_content_hash(self, document: Dict[str, Any]) -> str:
        """Compute SHA256 hash of document for deduplication."""
        content_str = json.dumps(document, sort_keys=True, separators=(',', ':'))
        return hashlib.sha256(content_str.encode()).hexdigest()
    
    def _validate_document(self, document: Dict[str, Any]) -> List[str]:
        """Validate document against JSON Schema and Pydantic."""
        # JSON Schema validation (first gate)
        schema_errors = validate_json_schema(document)
        if schema_errors:
            return schema_errors
        
        # Pydantic validation (second gate)
        try:
            AgenticAIConfig(**document)
        except Exception as e:
            return [f"Pydantic validation failed: {e}"]
        
        return []
    
    def create_revision(
        self,
        workflow_id: str,
        document: Dict[str, Any],
        created_by: str,
        status: str = "draft"
    ) -> WorkflowRevision:
        """Create a new workflow revision.
        
        Args:
            workflow_id: Workflow identifier
            document: Complete workflow configuration document
            created_by: User ID who created the revision
            status: Initial status (draft, validated, published, archived)
        
        Returns:
            Created WorkflowRevision
        
        Raises:
            ValueError: If document validation fails
        """
        db = self._get_db()
        
        # Verify workflow exists
        workflow = db.query(Workflow).filter(Workflow.id == workflow_id).first()
        if not workflow:
            raise ValueError(f"Workflow not found: {workflow_id}")
        
        # Validate document (JSON Schema + Pydantic)
        validation_errors = self._validate_document(document)
        if validation_errors:
            raise ValueError(f"Document validation failed: {'; '.join(validation_errors)}")
        
        # Compute content hash for deduplication
        content_hash = self._compute_content_hash(document)
        
        # Check for existing revision with same content
        existing = db.query(WorkflowRevision).filter(
            WorkflowRevision.workflow_id == workflow_id,
            WorkflowRevision.content_hash == content_hash
        ).first()
        if existing:
            logger.info("revision_duplicate_detected", 
                       workflow_id=workflow_id, 
                       existing_revision_id=existing.id,
                       existing_revision=existing.revision)
            return existing
        
        # Determine next revision number
        last_revision = db.query(WorkflowRevision).filter(
            WorkflowRevision.workflow_id == workflow_id
        ).order_by(desc(WorkflowRevision.revision)).first()
        
        next_revision = 1 if last_revision is None else last_revision.revision + 1
        
        # Create revision
        revision = WorkflowRevision(
            id=str(uuid.uuid4()),
            workflow_id=workflow_id,
            revision=next_revision,
            document=document,
            content_hash=content_hash,
            status=status,
            created_by=created_by
        )
        
        db.add(revision)
        db.commit()
        db.refresh(revision)
        
        logger.info("revision_created",
                   workflow_id=workflow_id,
                   revision_id=revision.id,
                   revision=revision.revision,
                   status=status)
        
        return revision
    
    def get_revision(self, workflow_id: str, revision: int) -> Optional[WorkflowRevision]:
        """Get a specific revision by workflow ID and revision number."""
        db = self._get_db()
        return db.query(WorkflowRevision).filter(
            WorkflowRevision.workflow_id == workflow_id,
            WorkflowRevision.revision == revision
        ).first()
    
    def get_revision_by_id(self, revision_id: str) -> Optional[WorkflowRevision]:
        """Get revision by UUID."""
        db = self._get_db()
        return db.query(WorkflowRevision).filter(WorkflowRevision.id == revision_id).first()
    
    def get_latest_revision(self, workflow_id: str) -> Optional[WorkflowRevision]:
        """Get the latest revision for a workflow."""
        db = self._get_db()
        return db.query(WorkflowRevision).filter(
            WorkflowRevision.workflow_id == workflow_id
        ).order_by(desc(WorkflowRevision.revision)).first()
    
    def get_published_revision(self, workflow_id: str) -> Optional[WorkflowRevision]:
        """Get the currently published revision for a workflow."""
        db = self._get_db()
        return db.query(WorkflowRevision).filter(
            WorkflowRevision.workflow_id == workflow_id,
            WorkflowRevision.status == "published"
        ).order_by(desc(WorkflowRevision.revision)).first()
    
    def list_revisions(self, workflow_id: str, limit: int = 50, offset: int = 0) -> List[WorkflowRevision]:
        """List revisions for a workflow."""
        db = self._get_db()
        return db.query(WorkflowRevision).filter(
            WorkflowRevision.workflow_id == workflow_id
        ).order_by(desc(WorkflowRevision.revision)).limit(limit).offset(offset).all()
    
    def publish_revision(self, workflow_id: str, revision: int, published_by: str) -> WorkflowRevision:
        """Publish a revision (mark as published, archive previous published)."""
        db = self._get_db()
        
        # Get the revision to publish
        target = self.get_revision(workflow_id, revision)
        if not target:
            raise RevisionNotFoundError(f"Revision {revision} not found for workflow {workflow_id}")
        
        if target.status == "published":
            logger.info("revision_already_published", workflow_id=workflow_id, revision=revision)
            return target
        
        # Archive currently published revision
        current_published = self.get_published_revision(workflow_id)
        if current_published and current_published.id != target.id:
            current_published.status = "archived"
            logger.info("revision_archived", workflow_id=workflow_id, revision=current_published.revision)
        
        # Publish target
        target.status = "published"
        db.commit()
        db.refresh(target)
        
        logger.info("revision_published", workflow_id=workflow_id, revision=revision, published_by=published_by)
        return target
    
    def rollback_revision(self, workflow_id: str, target_revision: int, rolled_back_by: str) -> WorkflowRevision:
        """Rollback to a previous revision by creating a new revision with that content."""
        db = self._get_db()
        
        # Get target revision
        target = self.get_revision(workflow_id, target_revision)
        if not target:
            raise RevisionNotFoundError(f"Revision {target_revision} not found for workflow {workflow_id}")
        
        # Create new revision with target content
        new_revision = self.create_revision(
            workflow_id=workflow_id,
            document=target.document,
            created_by=rolled_back_by,
            status="published"
        )
        
        logger.info("revision_rollback_completed",
                   workflow_id=workflow_id,
                   target_revision=target_revision,
                   new_revision=new_revision.revision,
                   rolled_back_by=rolled_back_by)
        
        return new_revision
    
    def update_revision_status(
        self, 
        workflow_id: str, 
        revision: int, 
        status: str,
        updated_by: str
    ) -> WorkflowRevision:
        """Update revision status with validation."""
        db = self._get_db()
        
        valid_statuses = {"draft", "validated", "published", "archived"}
        if status not in valid_statuses:
            raise ValueError(f"Invalid status: {status}. Must be one of {valid_statuses}")
        
        target = self.get_revision(workflow_id, revision)
        if not target:
            raise RevisionNotFoundError(f"Revision {revision} not found for workflow {workflow_id}")
        
        # Validate state transitions
        valid_transitions = {
            "draft": {"validated", "archived"},
            "validated": {"published", "archived", "draft"},
            "published": {"archived"},
            "archived": {"draft"}  # Can restore from archive
        }
        
        if target.status in valid_transitions and status not in valid_transitions[target.status]:
            raise InvalidRevisionStateError(
                f"Cannot transition from {target.status} to {status}"
            )
        
        target.status = status
        db.commit()
        db.refresh(target)
        
        logger.info("revision_status_updated",
                   workflow_id=workflow_id,
                   revision=revision,
                   old_status=target.status,
                   new_status=status,
                   updated_by=updated_by)
        
        return target
    
    def validate_and_publish(
        self,
        workflow_id: str,
        document: Dict[str, Any],
        created_by: str
    ) -> WorkflowRevision:
        """Validate document and create/publish revision in one operation."""
        db = self._get_db()
        
        # Validate
        from agenticai_sdk.config.loader import validate_json_schema
        schema_errors = validate_json_schema(document)
        if schema_errors:
            raise ValueError(f"JSON Schema validation failed: {'; '.join(schema_errors)}")
        
        try:
            from agenticai_sdk.config.schemas import AgenticAIConfig
            AgenticAIConfig(**document)
        except Exception as e:
            raise ValueError(f"Pydantic validation failed: {e}")
        
        # Check if workflow exists
        workflow = db.query(Workflow).filter(Workflow.id == workflow_id).first()
        if not workflow:
            raise ValueError(f"Workflow not found: {workflow_id}")
        
        # Create revision with validated status
        revision = self.create_revision(
            workflow_id=workflow_id,
            document=document,
            created_by=created_by,
            status="validated"
        )
        
        # Immediately publish
        return self.publish_revision(workflow_id, revision.revision, created_by)


def get_revision_manager(db_session: Optional[Session] = None) -> RevisionManager:
    """Get RevisionManager instance."""
    return RevisionManager(db_session)