import threading
import time

from runtime.execution_lease import ExecutionLeaseStore
from runtime.intent_recovery_worker import IntentRecoveryWorker
from runtime.reconciliation_journal import ReconciliationJournal
from runtime.tool_intent_store import ToolIntent, ToolIntentStore


def test_concurrent_recovery_workers_commit_one_terminal_effect(tmp_path):
    intents = ToolIntentStore(str(tmp_path / "intents.json"))
    leases = ExecutionLeaseStore(str(tmp_path / "leases.json"))
    journal = ReconciliationJournal(str(tmp_path / "journal.json"))
    intent = ToolIntent("e2e", "call", "send", {}, "execution-e2e", "ambiguous")
    intents.prepare(intent)

    calls = []
    calls_lock = threading.Lock()
    results = []
    results_lock = threading.Lock()

    def resolver(item):
        with calls_lock:
            calls.append(item.idempotency_key)
        # Deterministic contention: the lease holder stays inside the
        # resolver (holding the execution lease) until the other worker has
        # already attempted recovery and recorded its result. This removes
        # the scheduling race where one worker fully completes before the
        # other starts, which used to make this test flaky.
        deadline = time.monotonic() + 10.0
        while not results and time.monotonic() < deadline:
            time.sleep(0.005)
        return "completed", {"ok": True}

    def run(worker_id):
        worker = IntentRecoveryWorker(intents, leases, worker_id, journal)
        result = worker.recover_one(intent, resolver)
        with results_lock:
            results.append(result)

    threads = [threading.Thread(target=run, args=("worker-a",)), threading.Thread(target=run, args=("worker-b",))]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=10)

    assert len(results) == 2
    assert sum(result.status == "completed" for result in results) == 1
    assert sum(result.status == "skipped_by_lease" for result in results) == 1
    assert calls == ["e2e"]
    assert intents.get("e2e").state == "completed"
    assert journal.get("e2e").status == "completed"


def test_recovery_replay_after_concurrent_terminal_commit_has_no_second_effect(tmp_path):
    intents = ToolIntentStore(str(tmp_path / "intents.json"))
    leases = ExecutionLeaseStore(str(tmp_path / "leases.json"))
    journal = ReconciliationJournal(str(tmp_path / "journal.json"))
    intent = ToolIntent("replay", "call", "send", {}, "execution-replay", "ambiguous")
    intents.prepare(intent)

    calls = []
    worker = IntentRecoveryWorker(intents, leases, "worker-a", journal)
    first = worker.recover_one(intent, lambda item: calls.append(item.idempotency_key) or ("completed", {"ok": True}))
    second = worker.recover_one(intent, lambda item: calls.append(item.idempotency_key) or ("failed", None))

    assert first.status == "completed"
    assert second.status == "completed"
    assert second.reason == "journal_replay"
    assert calls == ["replay"]
    assert intents.get("replay").state == "completed"
