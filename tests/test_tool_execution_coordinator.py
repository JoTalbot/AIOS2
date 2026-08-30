import pytest

from runtime.execution_audit import ExecutionAuditLog
from runtime.execution_commit import ExecutionCommitCoordinator
from runtime.execution_store import ExecutionState, ExecutionStore
from runtime.tool_execution_coordinator import ToolExecutionCoordinator
from runtime.tool_idempotency_store import ToolIdempotencyStore
from runtime.tool_intent_store import ToolIntent, ToolIntentStore


def _make(tmp_path):
    executions = ExecutionStore(str(tmp_path / "executions.json"))
    audit = ExecutionAuditLog(str(tmp_path / "audit.jsonl"))
    commits = ExecutionCommitCoordinator(executions, audit, str(tmp_path / "commits.jsonl"))
    intents = ToolIntentStore(str(tmp_path / "intents.json"))
    results = ToolIdempotencyStore(str(tmp_path / "results.json"))
    return executions, intents, results, ToolExecutionCoordinator(intents, results, commits)


def test_tool_success_drives_execution_success_without_replay(tmp_path):
    executions, intents, results, coordinator = _make(tmp_path)
    state = ExecutionState("e1", status="running", attempt=1)
    executions.save(state)
    intents.prepare(ToolIntent("k", "call-1", "remote_write", {}, "e1"))
    assert intents.claim("k", "worker", "token") is not None

    first = coordinator.commit(
        state, key="k", call_id="call-1", tool="remote_write",
        owner_id="worker", claim_token="token", ok=True, value={"id": 7}
    )

    assert first.tool.committed is True
    assert first.execution is not None
    assert executions.get("e1").status == "completed"
    assert executions.get("e1").result == {"id": 7}
    assert results.get("k").value == {"id": 7}


def test_fenced_tool_commit_does_not_advance_execution(tmp_path):
    executions, intents, results, coordinator = _make(tmp_path)
    state = ExecutionState("e1", status="running", attempt=1)
    executions.save(state)
    intents.prepare(ToolIntent("k", "call-1", "remote_write", {}, "e1"))
    intents.claim("k", "worker", "token")

    result = coordinator.commit(
        state, key="k", call_id="call-1", tool="remote_write",
        owner_id="worker", claim_token="stale", ok=True, value={"id": 7}
    )

    assert result.tool.committed is False
    assert result.execution is None
    assert executions.get("e1").status == "running"
    assert results.get("k").value == {"id": 7}
