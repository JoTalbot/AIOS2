import pytest

from runtime.execution_boundary import ExecutionBoundary
from runtime.tool_idempotency_store import ToolIdempotencyStore
from runtime.tool_intent_store import ToolIntent, ToolIntentStore


def test_boundary_commit_is_idempotent_after_fenced_claim_loss(tmp_path):
    intents = ToolIntentStore(str(tmp_path / "intents.json"))
    results = ToolIdempotencyStore(str(tmp_path / "results.json"))
    boundary = ExecutionBoundary(intents, results)

    key = "tool:call-1"
    intents.prepare(ToolIntent(key, "call-1", "write", {}))
    first = intents.claim(key, "worker-a", "token-a")
    assert first is not None

    committed = boundary.commit(
        key=key,
        call_id="call-1",
        tool="write",
        owner_id="worker-a",
        claim_token="token-a",
        ok=True,
        value={"status": "done"},
    )
    assert committed.committed is True

    replay = boundary.commit(
        key=key,
        call_id="call-1",
        tool="write",
        owner_id="worker-b",
        claim_token="token-b",
        ok=True,
        value={"status": "different"},
    )
    assert replay.committed is False
    assert replay.value == {"status": "done"}
    assert results.get(key).value == {"status": "done"}


def test_boundary_preserves_durable_result_when_terminal_transition_is_fenced(tmp_path):
    intents = ToolIntentStore(str(tmp_path / "intents.json"))
    results = ToolIdempotencyStore(str(tmp_path / "results.json"))
    boundary = ExecutionBoundary(intents, results)

    key = "tool:call-2"
    intents.prepare(ToolIntent(key, "call-2", "write", {}))
    assert intents.claim(key, "worker-a", "token-a") is not None
    assert intents.release_claim(key, "worker-a", "token-a", "ambiguous") is not None
    assert intents.claim(key, "worker-b", "token-b") is not None

    stale = boundary.commit(
        key=key,
        call_id="call-2",
        tool="write",
        owner_id="worker-a",
        claim_token="token-a",
        ok=True,
        value={"winner": "stale"},
    )
    assert stale.committed is False

    authoritative = boundary.commit(
        key=key,
        call_id="call-2",
        tool="write",
        owner_id="worker-b",
        claim_token="token-b",
        ok=True,
        value={"winner": "current"},
    )
    assert authoritative.committed is True
    assert results.get(key).value == {"winner": "stale"}
