"""Tests for SQLAlchemy ORM models — create, query, relationships."""
from __future__ import annotations

import os
import uuid

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from agenticai_sdk.db import Base
from agenticai_sdk.db.models import (
    ApiKey,
    Plan,
    RAGSource,
    Tool,
    User,
    Workflow,
    Workspace,
    WorkspaceMember,
)


@pytest.fixture(autouse=True)
def _fresh_db():
    """Create a fresh in-memory SQLite database for each test."""
    engine = create_engine("sqlite://", echo=False)
    Base.metadata.create_all(bind=engine)
    TestSession = sessionmaker(bind=engine)
    session = TestSession()
    yield session
    session.close()
    engine.dispose()


class TestUser:
    def test_create_user(self, _fresh_db):
        uid = uuid.uuid4().hex
        user = User(
            id=uid,
            email=f"{uid}@example.com",
            hashed_password="hashed_pw",
            full_name="Test User",
            is_active=1,
        )
        _fresh_db.add(user)
        _fresh_db.commit()

        saved = _fresh_db.query(User).filter(User.id == uid).first()
        assert saved is not None
        assert saved.email == f"{uid}@example.com"
        assert saved.is_active == 1

    def test_user_soft_delete(self, _fresh_db):
        """Deactivate a user by setting is_active to 0."""
        uid = uuid.uuid4().hex
        user = User(id=uid, email=f"{uid}@example.com", hashed_password="pw", is_active=1)
        _fresh_db.add(user)
        _fresh_db.commit()

        user.is_active = 0
        _fresh_db.commit()

        saved = _fresh_db.query(User).filter(User.id == uid).first()
        assert saved.is_active == 0

    def test_unique_email(self, _fresh_db):
        uid1 = uuid.uuid4().hex
        user1 = User(id=uid1, email="dupe@example.com", hashed_password="pw", is_active=1)
        _fresh_db.add(user1)
        _fresh_db.commit()

        uid2 = uuid.uuid4().hex
        user2 = User(id=uid2, email="dupe@example.com", hashed_password="pw", is_active=1)
        _fresh_db.add(user2)
        with pytest.raises(Exception):
            _fresh_db.commit()


class TestWorkspace:
    def test_create_workspace(self, _fresh_db):
        uid = uuid.uuid4().hex
        user = User(id=uid, email=f"{uid}@example.com", hashed_password="pw")
        _fresh_db.add(user)

        ws_id = uuid.uuid4().hex
        ws = Workspace(id=ws_id, name="Test WS", owner_id=uid)
        _fresh_db.add(ws)
        _fresh_db.commit()

        saved = _fresh_db.query(Workspace).filter(Workspace.id == ws_id).first()
        assert saved.name == "Test WS"
        assert saved.owner_id == uid

    def test_workspace_owner_relationship(self, _fresh_db):
        uid = uuid.uuid4().hex
        user = User(id=uid, email=f"{uid}@example.com", hashed_password="pw")
        _fresh_db.add(user)

        ws = Workspace(id=uuid.uuid4().hex, name="Owner Test", owner_id=uid)
        _fresh_db.add(ws)
        _fresh_db.commit()

        assert ws.owner.email == user.email


class TestWorkspaceMember:
    def test_add_member(self, _fresh_db):
        uid = uuid.uuid4().hex
        user = User(id=uid, email=f"{uid}@example.com", hashed_password="pw")
        _fresh_db.add(user)

        ws_id = uuid.uuid4().hex
        ws = Workspace(id=ws_id, name="Member WS", owner_id=uid)
        _fresh_db.add(ws)

        member = WorkspaceMember(workspace_id=ws_id, user_id=uid, role="editor")
        _fresh_db.add(member)
        _fresh_db.commit()

        members = _fresh_db.query(WorkspaceMember).filter(WorkspaceMember.workspace_id == ws_id).all()
        assert len(members) == 1
        assert members[0].role == "editor"

    def test_member_user_relationship(self, _fresh_db):
        uid = uuid.uuid4().hex
        user = User(id=uid, email=f"{uid}@example.com", hashed_password="pw")
        _fresh_db.add(user)

        ws_id = uuid.uuid4().hex
        ws = Workspace(id=ws_id, name="Rel WS", owner_id=uid)
        _fresh_db.add(ws)

        member = WorkspaceMember(workspace_id=ws_id, user_id=uid, role="admin")
        _fresh_db.add(member)
        _fresh_db.commit()

        assert member.user.email == user.email
        assert member.workspace.name == "Rel WS"


class TestApiKey:
    def test_create_api_key(self, _fresh_db):
        uid = uuid.uuid4().hex
        user = User(id=uid, email=f"{uid}@example.com", hashed_password="pw")
        _fresh_db.add(user)

        ws_id = uuid.uuid4().hex
        ws = Workspace(id=ws_id, name="Key WS", owner_id=uid)
        _fresh_db.add(ws)

        key = ApiKey(
            id=uuid.uuid4().hex,
            workspace_id=ws_id,
            key_prefix="agk_test",
            key_hash="hashed_value",
            name="Test Key",
            is_active=1,
        )
        _fresh_db.add(key)
        _fresh_db.commit()

        saved = _fresh_db.query(ApiKey).filter(ApiKey.key_prefix == "agk_test").first()
        assert saved is not None
        assert saved.name == "Test Key"
        assert saved.is_active == 1

    def test_workflow_scoped_api_key(self, _fresh_db):
        uid = uuid.uuid4().hex
        user = User(id=uid, email=f"{uid}@example.com", hashed_password="pw")
        _fresh_db.add(user)

        ws_id = uuid.uuid4().hex
        ws = Workspace(id=ws_id, name="WF Key WS", owner_id=uid)
        _fresh_db.add(ws)

        wf_id = uuid.uuid4().hex
        wf = Workflow(id=wf_id, workspace_id=ws_id, name="Test WF", config={})
        _fresh_db.add(wf)

        key = ApiKey(
            id=uuid.uuid4().hex,
            workspace_id=ws_id,
            workflow_id=wf_id,
            key_prefix="wfk_test",
            key_hash="hashed_value",
            name="WF Key",
        )
        _fresh_db.add(key)
        _fresh_db.commit()

        saved = _fresh_db.query(ApiKey).filter(ApiKey.workflow_id == wf_id).first()
        assert saved is not None
        assert saved.key_prefix.startswith("wfk")

    def test_deactivate_previous_keys(self, _fresh_db):
        """When multiple keys exist for a workflow, only one should be active at a time."""
        uid = uuid.uuid4().hex
        user = User(id=uid, email=f"{uid}@example.com", hashed_password="pw")
        _fresh_db.add(user)

        ws_id = uuid.uuid4().hex
        ws = Workspace(id=ws_id, name="Deact WS", owner_id=uid)
        _fresh_db.add(ws)

        wf_id = uuid.uuid4().hex
        wf = Workflow(id=wf_id, workspace_id=ws_id, name="Deact WF", config={})
        _fresh_db.add(wf)

        # Create first key
        k1 = ApiKey(id=uuid.uuid4().hex, workspace_id=ws_id, workflow_id=wf_id,
                     key_prefix="wfk_old", key_hash="h1", name="Old Key", is_active=1)
        _fresh_db.add(k1)
        _fresh_db.commit()

        # Deactivate old keys and create new one
        _fresh_db.query(ApiKey).filter(
            ApiKey.workflow_id == wf_id, ApiKey.is_active == 1
        ).update({"is_active": 0})

        k2 = ApiKey(id=uuid.uuid4().hex, workspace_id=ws_id, workflow_id=wf_id,
                     key_prefix="wfk_new", key_hash="h2", name="New Key", is_active=1)
        _fresh_db.add(k2)
        _fresh_db.commit()

        active = _fresh_db.query(ApiKey).filter(
            ApiKey.workflow_id == wf_id, ApiKey.is_active == 1
        ).all()
        assert len(active) == 1
        assert active[0].key_prefix == "wfk_new"

    def test_api_key_belongs_to_workspace(self, _fresh_db):
        """Verify the FK relationship from ApiKey → Workspace."""
        uid = uuid.uuid4().hex
        user = User(id=uid, email=f"{uid}@example.com", hashed_password="pw")
        _fresh_db.add(user)

        ws = Workspace(id=uuid.uuid4().hex, name="Parent WS", owner_id=uid)
        _fresh_db.add(ws)

        key = ApiKey(id=uuid.uuid4().hex, workspace_id=ws.id,
                     key_prefix="agk_rel", key_hash="h", name="Rel Key")
        _fresh_db.add(key)
        _fresh_db.commit()

        assert key.workspace.name == "Parent WS"


class TestWorkflow:
    def test_create_workflow(self, _fresh_db):
        uid = uuid.uuid4().hex
        user = User(id=uid, email=f"{uid}@example.com", hashed_password="pw")
        _fresh_db.add(user)

        ws = Workspace(id=uuid.uuid4().hex, name="WF WS", owner_id=uid)
        _fresh_db.add(ws)

        wf = Workflow(
            id=uuid.uuid4().hex,
            workspace_id=ws.id,
            name="My Test Workflow",
            description="A workflow for testing",
            config={"agents": [], "edges": []},
        )
        _fresh_db.add(wf)
        _fresh_db.commit()

        saved = _fresh_db.query(Workflow).filter(Workflow.name == "My Test Workflow").first()
        assert saved is not None
        assert saved.description == "A workflow for testing"
        assert saved.config == {"agents": [], "edges": []}

    def test_workflow_belongs_to_workspace(self, _fresh_db):
        uid = uuid.uuid4().hex
        user = User(id=uid, email=f"{uid}@example.com", hashed_password="pw")
        _fresh_db.add(user)

        ws = Workspace(id=uuid.uuid4().hex, name="Parent", owner_id=uid)
        _fresh_db.add(ws)

        wf = Workflow(id=uuid.uuid4().hex, workspace_id=ws.id, name="Child WF", config={})
        _fresh_db.add(wf)
        _fresh_db.commit()

        assert wf.workspace.name == "Parent"


class TestRAGSource:
    def test_create_rag_source(self, _fresh_db):
        uid = uuid.uuid4().hex
        user = User(id=uid, email=f"{uid}@example.com", hashed_password="pw")
        _fresh_db.add(user)

        ws = Workspace(id=uuid.uuid4().hex, name="RAG WS", owner_id=uid)
        _fresh_db.add(ws)

        rag = RAGSource(
            id=uuid.uuid4().hex,
            workspace_id=ws.id,
            name="My Documents",
            provider="qdrant",
            config={"collection": "docs", "embedding_model": "text-embedding-3-small"},
        )
        _fresh_db.add(rag)
        _fresh_db.commit()

        saved = _fresh_db.query(RAGSource).filter(RAGSource.name == "My Documents").first()
        assert saved is not None
        assert saved.provider == "qdrant"


class TestTool:
    def test_create_tool(self, _fresh_db):
        uid = uuid.uuid4().hex
        user = User(id=uid, email=f"{uid}@example.com", hashed_password="pw")
        _fresh_db.add(user)

        ws = Workspace(id=uuid.uuid4().hex, name="Tool WS", owner_id=uid)
        _fresh_db.add(ws)

        tool = Tool(
            id=uuid.uuid4().hex,
            workspace_id=ws.id,
            name="web_search",
            description="Search the web",
            tool_type="api",
            code_or_url="https://api.example.com/search",
        )
        _fresh_db.add(tool)
        _fresh_db.commit()

        saved = _fresh_db.query(Tool).filter(Tool.name == "web_search").first()
        assert saved is not None
        assert saved.tool_type == "api"


class TestPlan:
    def test_create_plan(self, _fresh_db):
        plan = Plan(
            id="starter",
            name="Starter Plan",
            tokens_per_month=100000,
            max_workflows=5,
            max_api_keys=2,
            max_team_members=1,
            price_cents=0,
            features={"web_search": True},
        )
        _fresh_db.add(plan)
        _fresh_db.commit()

        saved = _fresh_db.query(Plan).filter(Plan.id == "starter").first()
        assert saved is not None
        assert saved.name == "Starter Plan"
        assert saved.price_cents == 0

    def test_plan_defaults(self, _fresh_db):
        plan = Plan(id="custom", name="Custom")
        _fresh_db.add(plan)
        _fresh_db.commit()

        assert plan.tokens_per_month == 100000
        assert plan.max_workflows == 5
        assert plan.max_api_keys == 2
        assert plan.max_team_members == 1
        assert plan.is_active is True
