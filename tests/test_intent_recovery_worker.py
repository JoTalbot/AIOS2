from runtime.execution_lease import ExecutionLeaseStore
from runtime.intent_recovery_worker import IntentRecoveryWorker
from runtime.tool_intent_store import ToolIntent, ToolIntentStore


def test_recovery_resolves_without_replaying_side_effect(tmp_path):
    intents = ToolIntentStore(str(tmp_path / "intents.json"))
    leases = ExecutionLeaseStore(str(tmp_path / "leases.json"))
    intent = ToolIntent("k", "call", "send", {}, "e1", "ambiguous")
    intents.prepare(intent)
    calls = []

    def resolver(item):
        calls.append(item.idempotency_key)
        return "completed", {"ok": True}

    result = IntentRecoveryWorker(intents, leases, "worker-a").recover_all(resolver)
    assert result[0].status == "completed"
    assert calls == ["k"]
    assert intents.pending() == []
