from runtime.execution_boundary import ExecutionBoundary
from runtime.execution_boundary_adapter import ToolExecutionBoundary
from runtime.tool_idempotency_store import ToolIdempotencyStore
from runtime.tool_intent_store import ToolIntent, ToolIntentStore
from runtime.tool_protocol import ToolCall, ToolResult


def test_adapter_commits_terminal_tool_result_through_fence(tmp_path):
    intents = ToolIntentStore(str(tmp_path / "intents.json"))
    results = ToolIdempotencyStore(str(tmp_path / "results.json"))
    call = ToolCall("remote_write", {"x": 1}, "call-1", idempotency_key="k")
    intents.prepare(ToolIntent("k", "call-1", "remote_write", {"x": 1}, "e"))
    assert intents.claim("k", "worker", "token") is not None

    result = ToolExecutionBoundary(ExecutionBoundary(intents, results)).commit(
        call, ToolResult.success(call, {"accepted": True}), "worker", "token"
    )

    assert result.ok and result.value == {"accepted": True}
    assert not result.ambiguous
    assert intents.get("k").state == "completed"
    assert results.get("k").value == {"accepted": True}


def test_adapter_does_not_terminally_commit_ambiguous_result(tmp_path):
    intents = ToolIntentStore(str(tmp_path / "intents.json"))
    results = ToolIdempotencyStore(str(tmp_path / "results.json"))
    call = ToolCall("remote_write", {}, "call-1", idempotency_key="k")
    intents.prepare(ToolIntent("k", "call-1", "remote_write", {}, "e"))
    intents.claim("k", "worker", "token")
    result = ToolResult.failure(call, TimeoutError("timeout"), retryable=False, ambiguous=True)

    returned = ToolExecutionBoundary(ExecutionBoundary(intents, results)).commit(
        call, result, "worker", "token"
    )

    assert returned.ambiguous
    assert intents.get("k").state == "executing"
    assert results.get("k") is None
