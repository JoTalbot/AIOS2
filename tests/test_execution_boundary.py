from runtime.execution_boundary import ExecutionBoundary
from runtime.tool_idempotency_store import ToolIdempotencyStore
from runtime.tool_intent_store import ToolIntent, ToolIntentStore


def test_commit_persists_result_before_terminal_claim(tmp_path):
    intents = ToolIntentStore(str(tmp_path / "intents.json"))
    results = ToolIdempotencyStore(str(tmp_path / "results.json"))
    intents.prepare(ToolIntent("k", "call-1", "remote_write", {"value": 1}, "e"))
    claimed = intents.claim("k", "worker-1", "token-1")
    assert claimed is not None

    outcome = ExecutionBoundary(intents, results).commit(
        key="k", call_id="call-1", tool="remote_write", owner_id="worker-1",
        claim_token="token-1", ok=True, value={"accepted": True}
    )

    assert outcome.committed is True
    assert results.get("k").value == {"accepted": True}
    assert intents.get("k").state == "completed"


def test_stale_worker_cannot_finalize_but_result_remains_durable(tmp_path):
    intents = ToolIntentStore(str(tmp_path / "intents.json"), claim_ttl_seconds=1)
    results = ToolIdempotencyStore(str(tmp_path / "results.json"))
    intents.prepare(ToolIntent("k", "call-1", "remote_write", {}, "e"))
    intents.claim("k", "old", "old-token")

    boundary = ExecutionBoundary(intents, results)
    outcome = boundary.commit(
        key="k", call_id="call-1", tool="remote_write", owner_id="old",
        claim_token="wrong-token", ok=False, error="remote failure"
    )

    assert outcome.committed is False
    assert results.get("k").error == "remote failure"
