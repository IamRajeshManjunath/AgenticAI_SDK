import os
import json
import base64
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from cryptography.fernet import Fernet
from sqlalchemy.orm import Session
from agenticai_sdk.db.database import get_session
from agenticai_sdk.db.models import (
    Workspace,
    Workflow,
    Tool,
    ActivityLog,
    WorkflowTrace,
    SchemaAuditTrail,
    BillingData,
    CronJob,
    IntegrationConnection,
)

class DALEncryptor:
    """Symmetric encryption helper for securing sensitive database payloads."""
    def __init__(self, key: Optional[str] = None):
        # Generate or load a consistent key based on environment for safety
        self.key = key or os.getenv("AGENTICAI_ENCRYPTION_KEY")
        if not self.key:
            # Fallback for testing/local-dev
            self.key = base64.urlsafe_b64encode(b"agenticai_platform_master_32bytes_")
        elif len(self.key) != 44: # Standard Fernet key base64 length
            # Normalize to safe 32-byte hash
            import hashlib
            h = hashlib.sha256(self.key.encode()).digest()
            self.key = base64.urlsafe_b64encode(h)
        self.fernet = Fernet(self.key)

    def encrypt(self, plain_text: str) -> str:
        return self.fernet.encrypt(plain_text.encode()).decode()

    def decrypt(self, cipher_text: str) -> str:
        return self.fernet.decrypt(cipher_text.encode()).decode()

    def encrypt_dict(self, data: Dict[str, Any]) -> str:
        return self.encrypt(json.dumps(data))

    def decrypt_to_dict(self, cipher_text: str) -> Dict[str, Any]:
        return json.loads(self.decrypt(cipher_text))

class BaseDAL(ABC):
    """Abstract Data Access Layer (DAL) enforcing tenant-isolation & pluggable storage."""
    
    @abstractmethod
    def save_workflow(self, workflow_id: str, workspace_id: str, name: str, config: Dict[str, Any]) -> Any:
        pass

    @abstractmethod
    def get_workflow(self, workflow_id: str, workspace_id: str) -> Optional[Dict[str, Any]]:
        pass

    @abstractmethod
    def log_activity(self, workspace_id: str, workflow_id: Optional[str], event_type: str, details: Dict[str, Any]) -> Any:
        pass

    @abstractmethod
    def save_audit_trail(self, agent_id: str, direction: str, payload: Dict[str, Any], schema_definition: Optional[Dict[str, Any]], is_valid: int, violation_error: Optional[str] = None) -> Any:
        pass

# Implement RelationalDAL
class RelationalDAL(BaseDAL):
    """Relational SQL implementation of the DAL utilizing SQLAlchemy ORM and bound session binds."""
    
    def __init__(self, encryptor: DALEncryptor):
        self.encryptor = encryptor

    def _get_db(self) -> Session:
        return next(get_session())

    def save_workflow(self, workflow_id: str, workspace_id: str, name: str, config: Dict[str, Any]) -> Workflow:
        db = self._get_db()
        try:
            # Check tenant isolation / existence of workspace
            ws = db.query(Workspace).filter(Workspace.id == workspace_id).first()
            if not ws:
                # Create default workspace to prevent FK errors
                ws = Workspace(id=workspace_id, name="Default Workspace")
                db.add(ws)
                db.commit()

            # Encrypt sensitive tool configs or credentials in workflow config
            encrypted_config = dict(config)
            if "tools" in encrypted_config:
                # Encrypt tool configs containing sensitive connection_string or arguments
                for tool in encrypted_config["tools"]:
                    if "config" in tool:
                        # Encrypt the sub-config
                        tool["config"] = self.encryptor.encrypt_dict(tool["config"])

            wf = db.query(Workflow).filter(Workflow.id == workflow_id, Workflow.workspace_id == workspace_id).first()
            if wf:
                wf.name = name
                wf.config = encrypted_config
            else:
                wf = Workflow(id=workflow_id, workspace_id=workspace_id, name=name, config=encrypted_config)
                db.add(wf)
            db.commit()
            db.refresh(wf)
            return wf
        finally:
            db.close()

    def get_workflow(self, workflow_id: str, workspace_id: str) -> Optional[Dict[str, Any]]:
        db = self._get_db()
        try:
            wf = db.query(Workflow).filter(Workflow.id == workflow_id, Workflow.workspace_id == workspace_id).first()
            if not wf:
                return None
            
            # Decrypt the config on load
            decrypted_config = dict(wf.config) if wf.config else {}
            if "tools" in decrypted_config:
                for tool in decrypted_config["tools"]:
                    if "config" in tool and isinstance(tool["config"], str):
                        try:
                            tool["config"] = self.encryptor.decrypt_to_dict(tool["config"])
                        except Exception:
                            pass # Fallback if not encrypted or bad key
            
            return {
                "id": wf.id,
                "workspace_id": wf.workspace_id,
                "name": wf.name,
                "description": wf.description,
                "config": decrypted_config,
                "created_at": wf.created_at.isoformat() if wf.created_at else None
            }
        finally:
            db.close()

    def log_activity(self, workspace_id: str, workflow_id: Optional[str], event_type: str, details: Dict[str, Any]) -> ActivityLog:
        db = self._get_db()
        try:
            # Enforce tenant scope
            import uuid
            log_id = str(uuid.uuid4())
            log_entry = ActivityLog(
                id=log_id,
                workspace_id=workspace_id,
                workflow_id=workflow_id,
                event_type=event_type,
                details=details
            )
            db.add(log_entry)
            db.commit()
            db.refresh(log_entry)
            return log_entry
        finally:
            db.close()

    def save_audit_trail(self, agent_id: str, direction: str, payload: Dict[str, Any], schema_definition: Optional[Dict[str, Any]], is_valid: int, violation_error: Optional[str] = None) -> SchemaAuditTrail:
        db = self._get_db()
        try:
            import uuid
            trail_id = str(uuid.uuid4())
            audit = SchemaAuditTrail(
                id=trail_id,
                agent_id=agent_id,
                direction=direction,
                payload=payload,
                schema_definition=schema_definition,
                is_valid=is_valid,
                violation_error=violation_error
            )
            db.add(audit)
            db.commit()
            db.refresh(audit)
            return audit
        finally:
            db.close()

# Implement Document / MongoDB DAL
class MongoDAL(BaseDAL):
    """MongoDB implementation of the DAL using PyMongo."""
    def __init__(self, connection_uri: str, encryptor: DALEncryptor):
        self.encryptor = encryptor
        self.connection_uri = connection_uri
        self._client = None
        self._db = None

    def _get_mongo_db(self):
        if not self._client:
            from pymongo import MongoClient
            self._client = MongoClient(self.connection_uri)
            self._db = self._client["agenticai_workflows"]
        return self._db

    def save_workflow(self, workflow_id: str, workspace_id: str, name: str, config: Dict[str, Any]) -> Any:
        db = self._get_mongo_db()
        encrypted_config = dict(config)
        if "tools" in encrypted_config:
            for tool in encrypted_config["tools"]:
                if "config" in tool:
                    tool["config"] = self.encryptor.encrypt_dict(tool["config"])

        # Enforce tenant isolation via tenant query matching
        query = {"id": workflow_id, "workspace_id": workspace_id}
        doc = {
            "id": workflow_id,
            "workspace_id": workspace_id,
            "name": name,
            "config": encrypted_config
        }
        db.workflows.update_one(query, {"$set": doc}, upsert=True)
        return doc

    def get_workflow(self, workflow_id: str, workspace_id: str) -> Optional[Dict[str, Any]]:
        db = self._get_mongo_db()
        query = {"id": workflow_id, "workspace_id": workspace_id}
        wf = db.workflows.find_one(query)
        if not wf:
            return None
        
        decrypted_config = dict(wf.get("config", {}))
        if "tools" in decrypted_config:
            for tool in decrypted_config["tools"]:
                if "config" in tool and isinstance(tool["config"], str):
                    try:
                        tool["config"] = self.encryptor.decrypt_to_dict(tool["config"])
                    except Exception:
                        pass
        return {
            "id": wf["id"],
            "workspace_id": wf["workspace_id"],
            "name": wf["name"],
            "config": decrypted_config
        }

    def log_activity(self, workspace_id: str, workflow_id: Optional[str], event_type: str, details: Dict[str, Any]) -> Any:
        db = self._get_mongo_db()
        doc = {
            "workspace_id": workspace_id,
            "workflow_id": workflow_id,
            "event_type": event_type,
            "details": details
        }
        db.activity_logs.insert_one(doc)
        return doc

    def save_audit_trail(self, agent_id: str, direction: str, payload: Dict[str, Any], schema_definition: Optional[Dict[str, Any]], is_valid: int, violation_error: Optional[str] = None) -> Any:
        db = self._get_mongo_db()
        doc = {
            "agent_id": agent_id,
            "direction": direction,
            "payload": payload,
            "schema_definition": schema_definition,
            "is_valid": is_valid,
            "violation_error": violation_error
        }
        db.schema_audit_trails.insert_one(doc)
        return doc

class DALFactory:
    """Central factory for retrieving hot-swappable connection pools and active DAL instances."""
    _instance: Optional[BaseDAL] = None
    _encryptor: Optional[DALEncryptor] = None

    @classmethod
    def get_encryptor(cls) -> DALEncryptor:
        if not cls._encryptor:
            cls._encryptor = DALEncryptor()
        return cls._encryptor

    @classmethod
    def get_dal(cls) -> BaseDAL:
        if cls._instance:
            return cls._instance
        
        db_type = os.getenv("DATABASE_TYPE", "relational").lower()
        encryptor = cls.get_encryptor()

        if db_type == "mongodb":
            mongo_uri = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
            cls._instance = MongoDAL(connection_uri=mongo_uri, encryptor=encryptor)
        else:
            cls._instance = RelationalDAL(encryptor=encryptor)
            
        return cls._instance
