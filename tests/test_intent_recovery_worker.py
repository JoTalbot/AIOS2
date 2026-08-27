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


def test_recovery_does_not_commit_after_lease_loss(tmp_path):
    intents = ToolIntentStore(str(tmp_path / "intents.json"))
    intent = ToolIntent("k", "call", "send", {}, "e1", "ambiguous")
    intents.prepare(intent)

    class ExpiringLeaseStore(ExecutionLeaseStore):
        def __init__(self, path):
            super().__init__(path, ttl_seconds=60)
            self.checks = 0

        def is_owner(self, execution_id, owner_id, fencing_token=None):
            self.checks += 1
            return self.checks == 1

    expiring = ExpiringLeaseStore(str(tmp_path / "leases.json"))
    result = IntentRecoveryWorker(intents, expiring, "worker-a").recover_one(
        intent, lambda item: ("completed", {"ok": True})
    )

    assert result.status == "lease_lost"
    assert intents.get("k").state == "ambiguous"
