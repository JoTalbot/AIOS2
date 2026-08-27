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


def test_recovery_uses_execution_id_for_lease_scope(tmp_path):
    intents = ToolIntentStore(str(tmp_path / "intents.json"))
    leases = ExecutionLeaseStore(str(tmp_path / "leases.json"))
    intent = ToolIntent("k", "call", "send", {}, "execution-1", "ambiguous")
    intents.prepare(intent)
    observed = []

    def resolver(item):
        observed.append(item)
        return "failed", None

    result = IntentRecoveryWorker(intents, leases, "worker-a").recover_one(intent, resolver)
    assert result.status == "failed"
    assert leases.is_owner("execution-1", "worker-a") is False
    assert observed[0].execution_id == "execution-1"


def test_recovery_fencing_loss_does_not_commit_claim(tmp_path):
    intents = ToolIntentStore(str(tmp_path / "intents.json"))
    leases = ExecutionLeaseStore(str(tmp_path / "leases.json"))
    intent = ToolIntent("k", "call", "send", {}, "e1", "ambiguous")
    intents.prepare(intent)
    worker = IntentRecoveryWorker(intents, leases, "worker-a")

    def resolver(item):
        current = leases.acquire("e1", "worker-a")
        assert current is not None
        assert leases.release("e1", "worker-a", current.fencing_token)
        rotated = leases.acquire("e1", "worker-b")
        assert rotated is not None
        return "completed", {"ok": True}

    result = worker.recover_one(intent, resolver)
    assert result.status == "skipped_by_lease"
    assert intents.get("k").state == "ambiguous"
