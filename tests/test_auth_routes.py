"""Tests for auth, API key, and RBAC endpoints."""
from __future__ import annotations

import os
import uuid

import pytest
from fastapi.testclient import TestClient

from agenticai_sdk.gateway.app import create_app


@pytest.fixture(autouse=True)
def _use_temp_db(tmp_path):
    """Force all tests to use a fresh temporary SQLite database."""
    db_path = tmp_path / "test.db"
    os.environ["AGENTICAI_DB_URL"] = f"sqlite:///{db_path}"
    yield
    os.environ.pop("AGENTICAI_DB_URL", None)


@pytest.fixture
def client():
    app = create_app(log_level="WARNING")
    return TestClient(app)


@pytest.fixture
def registered_user(client):
    """Register a test user and return their access token + user data."""
    email = f"test-{uuid.uuid4().hex[:8]}@example.com"
    resp = client.post("/auth/register", json={
        "email": email,
        "password": "strongpassword123",
        "full_name": "Test User",
        "workspace_name": "Test Workspace",
    })
    assert resp.status_code == 201
    data = resp.json()
    return {
        "email": email,
        "password": "strongpassword123",
        "access_token": data["access_token"],
        "user": data["user"],
    }


@pytest.fixture
def auth_headers(registered_user):
    return {"Authorization": f"Bearer {registered_user['access_token']}"}


# ── Registration & Login ──────────────────────────────────────────────


class TestRegister:
    def test_register_success(self, client):
        email = f"new-{uuid.uuid4().hex[:8]}@example.com"
        resp = client.post("/auth/register", json={
            "email": email,
            "password": "strongpassword123",
            "full_name": "New User",
        })
        assert resp.status_code == 201
        data = resp.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert data["user"]["email"] == email
        assert data["user"]["full_name"] == "New User"
        assert data["user"]["is_active"] is True
        assert data["user"]["default_workspace_id"] is not None

    def test_register_duplicate_email(self, client, registered_user):
        resp = client.post("/auth/register", json={
            "email": registered_user["email"],
            "password": "anotherpass123",
        })
        assert resp.status_code == 409
        assert "already exists" in resp.json()["detail"].lower()

    def test_register_short_password(self, client):
        resp = client.post("/auth/register", json={
            "email": f"short-{uuid.uuid4().hex[:8]}@example.com",
            "password": "short",
        })
        assert resp.status_code == 422


class TestLogin:
    def test_login_success(self, client, registered_user):
        resp = client.post("/auth/login", json={
            "email": registered_user["email"],
            "password": registered_user["password"],
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert data["user"]["email"] == registered_user["email"]

    def test_login_wrong_password(self, client, registered_user):
        resp = client.post("/auth/login", json={
            "email": registered_user["email"],
            "password": "wrongpassword",
        })
        assert resp.status_code == 401

    def test_login_nonexistent_user(self, client):
        resp = client.post("/auth/login", json={
            "email": "nobody@example.com",
            "password": "somepassword",
        })
        assert resp.status_code == 401


# ── Profile ───────────────────────────────────────────────────────────


class TestProfile:
    def test_get_me(self, client, auth_headers):
        resp = client.get("/auth/me", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "email" in data
        assert "id" in data

    def test_get_me_unauthenticated(self, client):
        resp = client.get("/auth/me")
        assert resp.status_code == 401

    def test_change_password(self, client, registered_user, auth_headers):
        new_password = "newstrongpass456"
        resp = client.put("/auth/me/password", headers=auth_headers, json={
            "current_password": registered_user["password"],
            "new_password": new_password,
        })
        assert resp.status_code == 204

        # Verify can login with new password
        login_resp = client.post("/auth/login", json={
            "email": registered_user["email"],
            "password": new_password,
        })
        assert login_resp.status_code == 200

    def test_change_password_wrong_current(self, client, auth_headers):
        resp = client.put("/auth/me/password", headers=auth_headers, json={
            "current_password": "wrongpassword",
            "new_password": "newpassword123",
        })
        assert resp.status_code == 400


# ── API Keys ──────────────────────────────────────────────────────────


class TestApiKeys:
    def test_create_api_key(self, client, auth_headers):
        resp = client.post("/auth/api-keys", headers=auth_headers, json={
            "name": "My Test Key",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "My Test Key"
        assert data["key"].startswith("agk_")
        assert len(data["key"]) > 20
        assert "id" in data

    def test_list_api_keys(self, client, auth_headers):
        # Create two keys
        client.post("/auth/api-keys", headers=auth_headers, json={"name": "Key 1"})
        client.post("/auth/api-keys", headers=auth_headers, json={"name": "Key 2"})

        resp = client.get("/auth/api-keys", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2
        names = [k["name"] for k in data]
        assert "Key 1" in names
        assert "Key 2" in names

    def test_delete_api_key(self, client, auth_headers):
        # Create a key
        create_resp = client.post("/auth/api-keys", headers=auth_headers, json={"name": "To Delete"})
        key_id = create_resp.json()["id"]

        resp = client.delete(f"/auth/api-keys/{key_id}", headers=auth_headers)
        assert resp.status_code == 204

        # Verify it's gone
        list_resp = client.get("/auth/api-keys", headers=auth_headers)
        assert len(list_resp.json()) == 0

    def test_delete_nonexistent_key(self, client, auth_headers):
        resp = client.delete(f"/auth/api-keys/{uuid.uuid4().hex}", headers=auth_headers)
        assert resp.status_code == 404

    def test_api_key_cannot_access_user_endpoints(self, client, auth_headers):
        """API keys authenticate at workspace level — cannot access /auth/me (needs user JWT)."""
        create_resp = client.post("/auth/api-keys", headers=auth_headers, json={"name": "Auth Test Key"})
        raw_key = create_resp.json()["key"]

        resp = client.get("/auth/me", headers={"X-API-Key": raw_key})
        assert resp.status_code == 401

    def test_api_key_auth_invalid(self, client):
        resp = client.get("/auth/me", headers={"X-API-Key": "agk_invalidkey123"})
        assert resp.status_code == 401


# ── Workflow-scoped API Keys ──────────────────────────────────────────


class TestWorkflowApiKeys:
    def _create_workflow_in_user_workspace(self, db, workspace_id):
        """Helper to create a workflow in the user's actual workspace."""
        from agenticai_sdk.db.models import Workflow
        wf = Workflow(
            id=f"wf-{uuid.uuid4().hex[:8]}",
            workspace_id=workspace_id,
            name="Test Workflow",
            config={"test": True},
        )
        db.add(wf)
        db.commit()
        return wf.id

    def test_create_workflow_api_key(self, client, auth_headers, registered_user):
        workspace_id = registered_user["user"]["default_workspace_id"]
        from agenticai_sdk.db import get_session
        db = next(get_session())
        try:
            wf_id = self._create_workflow_in_user_workspace(db, workspace_id)
        finally:
            db.close()

        resp = client.post(f"/auth/api-keys/workflow/{wf_id}", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["key"].startswith("wfk_")
        assert "id" in data

    def test_workflow_api_key_not_found(self, client, auth_headers):
        resp = client.post(f"/auth/api-keys/workflow/{uuid.uuid4().hex}", headers=auth_headers)
        assert resp.status_code == 404

    def test_workflow_key_cannot_access_user_endpoints(self, client, auth_headers, registered_user):
        """Workflow keys are workspace-scoped — cannot access /auth/me."""
        workspace_id = registered_user["user"]["default_workspace_id"]
        from agenticai_sdk.db import get_session
        db = next(get_session())
        try:
            wf_id = self._create_workflow_in_user_workspace(db, workspace_id)
        finally:
            db.close()

        create_resp = client.post(f"/auth/api-keys/workflow/{wf_id}", headers=auth_headers)
        raw_key = create_resp.json()["key"]

        resp = client.get("/auth/me", headers={"X-API-Key": raw_key})
        assert resp.status_code == 401


# ── Workspace Members ─────────────────────────────────────────────────


class TestWorkspaceMembers:
    def test_list_members(self, client, registered_user, auth_headers):
        resp = client.get("/auth/workspace/members", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["email"] == registered_user["email"]
        assert data[0]["role"] == "admin"

    def test_list_members_requires_auth(self, client):
        resp = client.get("/auth/workspace/members")
        assert resp.status_code == 401

    def test_invite_member_not_found(self, client, auth_headers):
        resp = client.post("/auth/workspace/invite", headers=auth_headers, json={
            "email": "nonexistent@example.com",
            "role": "editor",
        })
        assert resp.status_code == 404
        assert "register first" in resp.json()["detail"].lower()

    def test_invite_and_remove_member(self, client, auth_headers):
        """Register a second user, invite them, list members, remove them."""
        # Register second user
        second_email = f"second-{uuid.uuid4().hex[:8]}@example.com"
        second_resp = client.post("/auth/register", json={
            "email": second_email,
            "password": "password123",
        })
        assert second_resp.status_code == 201

        # Invite second user
        invite_resp = client.post("/auth/workspace/invite", headers=auth_headers, json={
            "email": second_email,
            "role": "editor",
        })
        assert invite_resp.status_code == 201

        # List members should show 2
        list_resp = client.get("/auth/workspace/members", headers=auth_headers)
        members = list_resp.json()
        assert len(members) == 2

        # Find second user's ID
        second_member = [m for m in members if m["email"] == second_email][0]
        second_user_id = second_member["user_id"]

        # Update role to viewer
        update_resp = client.put(
            f"/auth/workspace/members/{second_user_id}/role",
            headers=auth_headers,
            json={"role": "viewer"},
        )
        assert update_resp.status_code == 200

        # Verify role updated
        list_resp2 = client.get("/auth/workspace/members", headers=auth_headers)
        updated = [m for m in list_resp2.json() if m["user_id"] == second_user_id][0]
        assert updated["role"] == "viewer"

        # Remove member
        remove_resp = client.delete(
            f"/auth/workspace/members/{second_user_id}",
            headers=auth_headers,
        )
        assert remove_resp.status_code == 204

        # Verify only 1 member remains
        final_list = client.get("/auth/workspace/members", headers=auth_headers)
        assert len(final_list.json()) == 1

    def test_cannot_remove_last_admin(self, client, auth_headers, registered_user):
        """Should not allow removing the last admin."""
        list_resp = client.get("/auth/workspace/members", headers=auth_headers)
        admin_id = list_resp.json()[0]["user_id"]

        resp = client.delete(f"/auth/workspace/members/{admin_id}", headers=auth_headers)
        assert resp.status_code == 400
        assert "last admin" in resp.json()["detail"].lower()


# ── RBAC ──────────────────────────────────────────────────────────────


class TestRBAC:
    @pytest.fixture
    def second_user(self, client, registered_user):
        """Register a second user, then re-issue their token scoped to admin's workspace."""
        email = f"editor-{uuid.uuid4().hex[:8]}@example.com"
        resp = client.post("/auth/register", json={
            "email": email,
            "password": "password123",
        })
        data = resp.json()
        user_data = data["user"]
        admin_ws_id = registered_user["user"]["default_workspace_id"]

        # Re-issue JWT scoped to the admin's workspace so RBAC checks
        # resolve the editor's role inside the correct workspace.
        import jwt as pyjwt
        from datetime import datetime, timedelta, timezone
        from agenticai_sdk.auth.dependencies import SECRET_KEY as JWT_SECRET
        scoped_token = pyjwt.encode({
            "sub": user_data["id"],
            "workspace_id": admin_ws_id,
            "exp": datetime.now(timezone.utc) + timedelta(days=7),
            "iat": datetime.now(timezone.utc),
        }, JWT_SECRET, algorithm="HS256")

        return {
            "email": email,
            "access_token": scoped_token,
            "user": user_data,
        }

    def test_editor_can_list_members(self, client, auth_headers, second_user):
        """Editor role should be able to list members (require_role('admin', 'editor'))."""
        # Admin invites second user as editor
        client.post("/auth/workspace/invite", headers=auth_headers, json={
            "email": second_user["email"],
            "role": "editor",
        })

        editor_headers = {"Authorization": f"Bearer {second_user['access_token']}"}

        # Editor lists members
        resp = client.get("/auth/workspace/members", headers=editor_headers)
        assert resp.status_code == 200

    def test_editor_cannot_invite(self, client, auth_headers, second_user):
        """Editor should NOT be able to invite (require_admin)."""
        # Invite second user as editor
        client.post("/auth/workspace/invite", headers=auth_headers, json={
            "email": second_user["email"],
            "role": "editor",
        })

        editor_headers = {"Authorization": f"Bearer {second_user['access_token']}"}

        # Editor tries to invite a third user
        third_email = f"third-{uuid.uuid4().hex[:8]}@example.com"
        client.post("/auth/register", json={
            "email": third_email,
            "password": "password123",
        })

        resp = client.post("/auth/workspace/invite", headers=editor_headers, json={
            "email": third_email,
            "role": "viewer",
        })
        assert resp.status_code == 403

    def test_editor_cannot_remove(self, client, auth_headers, second_user):
        """Editor should NOT be able to remove members (require_admin)."""
        client.post("/auth/workspace/invite", headers=auth_headers, json={
            "email": second_user["email"],
            "role": "editor",
        })

        editor_headers = {"Authorization": f"Bearer {second_user['access_token']}"}

        resp = client.delete("/auth/workspace/members/some-id", headers=editor_headers)
        assert resp.status_code == 403

    def test_unauthenticated_cannot_list_workflows(self, client):
        resp = client.get("/api/v1/workflow/workflows")
        assert resp.status_code == 401
