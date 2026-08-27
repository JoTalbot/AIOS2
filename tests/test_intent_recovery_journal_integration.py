from runtime.execution_lease import ExecutionLeaseStore
from runtime.intent_recovery_worker import IntentRecoveryWorker
from runtime.reconciliation_journal import ReconciliationJournal
from runtime.tool_intent_store import ToolIntent, ToolIntentStore


def test_recovery_journal_makes_terminal_reconciliation_idempotent(tmp_path):
    intents = ToolIntentStore(str(tmp_path / "intents.json"))
    leases = ExecutionLeaseStore(str(tmp_path / "leases.json"))
    journal = ReconciliationJournal(str(tmp_path / "journal.json"))
    intent = ToolIntent("k", "call", "send", {}, "e1", "ambiguous")
    intents.prepare(intent)
    calls = []

    def resolver(item):
        calls.append(item.idempotency_key)
        return "completed", {"remote": "accepted"}

    worker = IntentRecoveryWorker(intents, leases, "worker-a", journal)
    first = worker.recover_one(intent, resolver)
    assert first.status == "completed"
    assert journal.get("k").status == "completed"
    assert journal.get("k").result == {"remote": "accepted"}
    assert calls == ["k"]


def test_recovery_journal_terminal_record_is_not_replayed(tmp_path):
    intents = ToolIntentStore(str(tmp_path / "intents.json"))
    leases = ExecutionLeaseStore(str(tmp_path / "leases.json"))
    journal = ReconciliationJournal(str(tmp_path / "journal.json"))
    journal.complete("k", {"remote": "already-accepted"})
    intent = ToolIntent("k", "call", "send", {}, "e1", "ambiguous")
    intents.prepare(intent)
    calls = []

    def resolver(item):
        calls.append(item.idempotency_key)
        raise AssertionError("terminal reconciliation must not replay")

    result = IntentRecoveryWorker(intents, leases, "worker-a", journal).recover_one(intent, resolver)
    assert result.status == "completed"
    assert calls == []
