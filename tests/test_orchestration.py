"""
Tests for the orchestration sub-package — schema mapper, HITL breakpoints,
fallback router, and consensus broker.
"""

from __future__ import annotations

import pytest

from agenticai_sdk.orchestration.schema_mapper import SchemaMapperEngine
from agenticai_sdk.orchestration.hitl_breakpoints import (
    HITLApprovalPayload,
    HITLBreakpointManager,
)
from agenticai_sdk.orchestration.consensus_broker import ConsensusBroker, _text_similarity


# ── SchemaMapperEngine tests ────────────────────────────────────────────────


def test_schema_mapper_exact_match():
    mapper = SchemaMapperEngine()
    payload = {"user_id": "123", "user_name": "Alice"}
    expected = {"user_id": "str", "user_name": "str"}

    result = mapper.auto_resolve(payload, expected)
    assert result == {"user_id": "123", "user_name": "Alice"}


def test_schema_mapper_case_insensitive():
    mapper = SchemaMapperEngine()
    payload = {"UserId": "123", "UserName": "Alice"}
    expected = {"user_id": "str", "user_name": "str"}

    result = mapper.auto_resolve(payload, expected)
    assert "user_id" in result
    assert result["user_id"] == "123"


def test_schema_mapper_camel_to_snake():
    mapper = SchemaMapperEngine()
    payload = {"firstName": "Alice", "lastName": "Smith"}
    expected = {"first_name": "str", "last_name": "str"}

    result = mapper.auto_resolve(payload, expected)
    assert "first_name" in result
    assert result["first_name"] == "Alice"


def test_schema_mapper_fuzzy_match():
    mapper = SchemaMapperEngine(fuzzy_threshold=0.6)
    payload = {"usr_name": "Alice", "usr_id": "123"}
    expected = {"user_name": "str", "user_id": "str"}

    result = mapper.auto_resolve(payload, expected)
    assert "user_name" in result or "usr_name" in result


def test_schema_mapper_caching():
    mapper = SchemaMapperEngine()
    payload = {"a": 1, "b": 2}
    expected = {"a": "int", "b": "int"}

    # First call populates cache
    mapper.auto_resolve(payload, expected)
    # Second call should use cache
    result = mapper.auto_resolve(payload, expected)
    assert result == {"a": 1, "b": 2}


def test_schema_mapper_clear_cache():
    mapper = SchemaMapperEngine()
    payload = {"x": 1}
    mapper.auto_resolve(payload, {"x": "int"})
    mapper.clear_cache()
    assert len(mapper._schema_cache) == 0


# ── HITLBreakpointManager tests ─────────────────────────────────────────────


@pytest.mark.asyncio
async def test_hitl_freeze_and_thaw_state(tmp_path):
    manager = HITLBreakpointManager(storage_dir=str(tmp_path))

    state = {"messages": ["hello"], "scratchpad": {"key": "value"}, "next_step": None}
    token = await manager.freeze_state(state, checkpoint_id="cp1", workflow_id="wf1")

    assert token.startswith("hitl_")

    restored = await manager.thaw_state(token)
    assert restored["scratchpad"]["key"] == "value"


@pytest.mark.asyncio
async def test_hitl_thaw_with_overrides(tmp_path):
    manager = HITLBreakpointManager(storage_dir=str(tmp_path))

    state = {"scratchpad": {"x": 1}, "messages": []}
    token = await manager.freeze_state(state, checkpoint_id="cp2")

    restored = await manager.thaw_state(token, overrides={"scratchpad": {"x": 999}})
    assert restored["scratchpad"]["x"] == 999


@pytest.mark.asyncio
async def test_hitl_submit_approval(tmp_path):
    manager = HITLBreakpointManager(storage_dir=str(tmp_path))

    state = {"messages": [], "scratchpad": {}}
    token = await manager.freeze_state(state, checkpoint_id="cp3")

    manager.submit_approval(token, approved=True, reviewer="admin")
    result = manager._pending_approvals.get(token)
    assert result is not None
    assert result.approved is True
    assert result.reviewer == "admin"


@pytest.mark.asyncio
async def test_hitl_dispatch_api_wait(tmp_path):
    manager = HITLBreakpointManager(storage_dir=str(tmp_path))

    payload = HITLApprovalPayload(
        workflow_id="wf1",
        agent_id="agent1",
        thread_id="t1",
        freeze_token="tok1",
        state_summary="Test summary",
        action_url="http://localhost:8000/approve",
        timestamp="2024-01-01T00:00:00Z",
    )

    result = await manager.dispatch_approval_request("api_wait", payload)
    assert result is True


# ── ConsensusBroker tests ───────────────────────────────────────────────────


def test_text_similarity_identical():
    score = _text_similarity("hello world foo bar", "hello world foo bar")
    assert score == 1.0


def test_text_similarity_completely_different():
    score = _text_similarity("apple banana cherry", "xyz uvw rst")
    assert score < 0.2


def test_text_similarity_partial():
    score = _text_similarity("the quick brown fox jumps", "the quick brown cat leaps")
    assert 0.3 < score < 0.9


def test_text_similarity_empty():
    assert _text_similarity("", "") == 1.0
    assert _text_similarity("hello", "") == 0.0
    assert _text_similarity("", "hello") == 0.0


def test_consensus_generate_temperatures():
    temps = ConsensusBroker._generate_temperatures(3, 0.2, 0.8)
    assert len(temps) == 3
    assert temps[0] == 0.2
    assert temps[-1] == 0.8


def test_consensus_generate_single_temperature():
    temps = ConsensusBroker._generate_temperatures(1, 0.2, 0.8)
    assert len(temps) == 1
    assert temps[0] == 0.5
