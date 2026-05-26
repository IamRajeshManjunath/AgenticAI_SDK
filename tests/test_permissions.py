"""Tests for the IAM permission system — policy evaluation engine and matching."""
from __future__ import annotations

import pytest

from agenticai_sdk.auth.permissions import (
    _match_pattern,
    _match_resource_pattern,
    evaluate_policies,
    ADMIN_POLICY_DOCUMENT,
    EDITOR_POLICY_DOCUMENT,
    VIEWER_POLICY_DOCUMENT,
)


# ── Pattern Matching ──────────────────────────────────────────────────────────


class TestMatchPattern:
    """Test ``_match_pattern`` for action wildcard matching."""

    def test_exact_match(self):
        assert _match_pattern("workflow:run", "workflow:run") is True

    def test_wildcard_all(self):
        assert _match_pattern("*", "anything:at:all") is True

    def test_category_wildcard(self):
        assert _match_pattern("workflow:*", "workflow:run") is True
        assert _match_pattern("workflow:*", "workflow:create") is True

    def test_category_wildcard_no_match(self):
        assert _match_pattern("workflow:*", "apikey:create") is False

    def test_no_match(self):
        assert _match_pattern("workflow:run", "workflow:delete") is False

    def test_prefix_not_wildcard(self):
        """``workflow:`` should NOT match ``workflow:run`` (no trailing ``*``)."""
        assert _match_pattern("workflow:", "workflow:run") is False


class TestMatchResourcePattern:
    """Test ``_match_resource_pattern`` for resource ARN matching."""

    def test_wildcard_all(self):
        assert _match_resource_pattern("*", "workspace:abc/*") is True

    def test_workspace_all(self):
        assert _match_resource_pattern("workspace:abc/*", "workspace:abc/workflow:wf1") is True
        assert _match_resource_pattern("workspace:abc/*", "workspace:abc/tool:t1") is True

    def test_workspace_specific(self):
        assert _match_resource_pattern(
            "workspace:abc/workflow:wf1",
            "workspace:abc/workflow:wf1",
        ) is True

    def test_different_workspace(self):
        assert _match_resource_pattern("workspace:abc/*", "workspace:xyz/workflow:wf1") is False

    def test_different_resource_type(self):
        assert _match_resource_pattern("workspace:abc/workflow:wf1", "workspace:abc/tool:t1") is False


# ── Policy Evaluation ─────────────────────────────────────────────────────────


class TestEvaluatePolicies:
    """Test the AWS IAM-style policy evaluation engine."""

    RESOURCE = "workspace:test-ws/*"

    def test_admin_allows_everything(self):
        policies = [ADMIN_POLICY_DOCUMENT]
        assert evaluate_policies(policies, "workflow:delete", self.RESOURCE) is True
        assert evaluate_policies(policies, "billing:cancel", self.RESOURCE) is True
        assert evaluate_policies(policies, "db:reset", self.RESOURCE) is True
        assert evaluate_policies(policies, "admin:superuser", self.RESOURCE) is True

    def test_viewer_allows_read_only(self):
        policies = [VIEWER_POLICY_DOCUMENT]
        assert evaluate_policies(policies, "workflow:read", self.RESOURCE) is True
        assert evaluate_policies(policies, "workflow:run", self.RESOURCE) is True
        assert evaluate_policies(policies, "tool:read", self.RESOURCE) is True
        assert evaluate_policies(policies, "member:list", self.RESOURCE) is True

    def test_viewer_denies_write_actions(self):
        policies = [VIEWER_POLICY_DOCUMENT]
        assert evaluate_policies(policies, "workflow:create", self.RESOURCE) is False
        assert evaluate_policies(policies, "workflow:delete", self.RESOURCE) is False
        assert evaluate_policies(policies, "tool:create", self.RESOURCE) is False
        assert evaluate_policies(policies, "member:invite", self.RESOURCE) is False

    def test_editor_allows_most_things(self):
        policies = [EDITOR_POLICY_DOCUMENT]
        assert evaluate_policies(policies, "workflow:create", self.RESOURCE) is True
        assert evaluate_policies(policies, "workflow:delete", self.RESOURCE) is True
        assert evaluate_policies(policies, "tool:create", self.RESOURCE) is True
        assert evaluate_policies(policies, "rag:delete", self.RESOURCE) is True
        assert evaluate_policies(policies, "apikey:create", self.RESOURCE) is True
        assert evaluate_policies(policies, "apikey:read", self.RESOURCE) is True

    def test_editor_denies_admin_actions(self):
        policies = [EDITOR_POLICY_DOCUMENT]
        assert evaluate_policies(policies, "member:invite", self.RESOURCE) is False
        assert evaluate_policies(policies, "member:remove", self.RESOURCE) is False
        assert evaluate_policies(policies, "member:update-role", self.RESOURCE) is False
        assert evaluate_policies(policies, "apikey:delete", self.RESOURCE) is False
        assert evaluate_policies(policies, "workspace:delete", self.RESOURCE) is False
        assert evaluate_policies(policies, "billing:*", self.RESOURCE) is False
        assert evaluate_policies(policies, "db:connect", self.RESOURCE) is False
        assert evaluate_policies(policies, "role:create", self.RESOURCE) is False

    def test_implicit_deny_when_no_policies_match(self):
        """If no statement matches, the result should be DENY."""
        policies = [VIEWER_POLICY_DOCUMENT]
        assert evaluate_policies(policies, "nonexistent:action", self.RESOURCE) is False

    def test_implicit_deny_empty_policy_list(self):
        assert evaluate_policies([], "workflow:run", self.RESOURCE) is False

    def test_explicit_deny_overrides_allow(self):
        """If one policy Allows but another Denies, Deny wins."""
        deny_billing = {
            "version": "1",
            "statements": [
                {"effect": "Allow", "actions": ["*"], "resources": ["*"]},
                {"effect": "Deny", "actions": ["billing:*"], "resources": ["*"]},
            ],
        }
        assert evaluate_policies([deny_billing], "billing:cancel", self.RESOURCE) is False
        assert evaluate_policies([deny_billing], "workflow:run", self.RESOURCE) is True

    def test_multi_policy_union(self):
        """Multiple policies attached to the same principal."""
        p1 = {
            "version": "1",
            "statements": [{"effect": "Allow", "actions": ["workflow:run"], "resources": ["*"]}],
        }
        p2 = {
            "version": "1",
            "statements": [{"effect": "Allow", "actions": ["tool:read"], "resources": ["*"]}],
        }
        assert evaluate_policies([p1, p2], "workflow:run", self.RESOURCE) is True
        assert evaluate_policies([p1, p2], "tool:read", self.RESOURCE) is True
        assert evaluate_policies([p1, p2], "workflow:create", self.RESOURCE) is False

    def test_statement_actions_list(self):
        """A statement can list multiple actions."""
        policy = {
            "version": "1",
            "statements": [{
                "effect": "Allow",
                "actions": ["workflow:read", "workflow:run", "tool:read"],
                "resources": ["*"],
            }],
        }
        assert evaluate_policies([policy], "workflow:read", self.RESOURCE) is True
        assert evaluate_policies([policy], "workflow:run", self.RESOURCE) is True
        assert evaluate_policies([policy], "tool:read", self.RESOURCE) is True
        assert evaluate_policies([policy], "workflow:create", self.RESOURCE) is False

    def test_resource_scoping(self):
        """Verify that resource patterns restrict access."""
        policy = {
            "version": "1",
            "statements": [{
                "effect": "Allow",
                "actions": ["*"],
                "resources": ["workspace:allowed-ws/*"],
            }],
        }
        assert evaluate_policies([policy], "workflow:run", "workspace:allowed-ws/workflow:wf1") is True
        assert evaluate_policies([policy], "workflow:run", "workspace:other-ws/workflow:wf1") is False

    def test_mixed_deny_and_allow_statements_same_policy(self):
        """A single policy with both Allow and Deny statements."""
        policy = {
            "version": "1",
            "statements": [
                {"effect": "Allow", "actions": ["workflow:*"], "resources": ["*"]},
                {"effect": "Deny", "actions": ["workflow:delete"], "resources": ["*"]},
            ],
        }
        assert evaluate_policies([policy], "workflow:run", self.RESOURCE) is True
        assert evaluate_policies([policy], "workflow:create", self.RESOURCE) is True
        assert evaluate_policies([policy], "workflow:delete", self.RESOURCE) is False

    def test_deny_all_statements(self):
        """Explicit Deny on * should deny everything."""
        policy = {
            "version": "1",
            "statements": [{"effect": "Deny", "actions": ["*"], "resources": ["*"]}],
        }
        assert evaluate_policies([policy], "workflow:run", self.RESOURCE) is False
        assert evaluate_policies([policy], "anything:else", self.RESOURCE) is False
