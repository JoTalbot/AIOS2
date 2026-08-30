from runtime.execution_boundary import ExecutionBoundary
from runtime.tool_idempotency_store import ToolIdempotencyStore
from runtime.tool_intent_store import ToolIntent, ToolIntentStore


def test_crash_after_external_effect_is_reconciled_without_reexecution(tmp_path):
    intents = ToolIntentStore(str(tmp_path / "intents.json"))
    results = ToolIdempotencyStore(str(tmp_path / "results.json"))
    boundary = ExecutionBoundary(intents, results)

    key = "tool:crash-1"
    intents.prepare(ToolIntent(key, "crash-1", "write", {}))
    assert intents.claim(key, "worker-a", "token-a") is not None

    # External provider reports success, but the process dies before commit().
    assert intents.release_claim(key, "worker-a", "token-a", "ambiguous") is True
    assert intents.get(key).state == "ambiguous"

    # Recovery must reconcile the durable provider result, not execute blindly.
    results.put_if_absent(
        __import__("runtime.tool_idempotency_store", fromlist=["StoredToolResult"]).StoredToolResult(
            key, "crash-1", "write", True, {"provider_id": "p-1"}, None
        )
    )
    reconciled = intents.finalize_from_journal(key, "completed")

    assert reconciled.state == "completed"
    assert results.get(key).value == {"provider_id": "p-1"}
    assert boundary.results.get(key).value == {"provider_id": "p-1"}


def test_ambiguous_intent_without_durable_result_stays_ambiguous(tmp_path):
    intents = ToolIntentStore(str(tmp_path / "intents.json"))
    results = ToolIdempotencyStore(str(tmp_path / "results.json"))

    key = "tool:crash-2"
    intents.prepare(ToolIntent(key, "crash-2", "write", {}))
    assert intents.claim(key, "worker-a", "token-a") is not None
    assert intents.release_claim(key, "worker-a", "token-a", "ambiguous") is True

    assert results.get(key) is None
    assert intents.get(key).state == "ambiguous"
