from runtime.execution_lease import ExecutionLeaseStore
from runtime.reconciliation_journal import ReconciliationJournal


def test_stale_worker_cannot_publish_terminal_journal_after_takeover(tmp_path):
    leases = ExecutionLeaseStore(str(tmp_path / "leases.json"), ttl_seconds=1)
    journal = ReconciliationJournal(str(tmp_path / "journal.json"))

    execution_id = "exec-1"
    first = leases.acquire(execution_id, "worker-a")
    assert first is not None

    # Simulate expiry/takeover without allowing the stale worker to retain authority.
    current = leases._read()[execution_id]
    current["expires_at"] = "2000-01-01T00:00:00+00:00"
    leases._write({execution_id: current})
    second = leases.acquire(execution_id, "worker-b")
    assert second is not None
    assert second.fencing_token > first.fencing_token

    assert leases.is_owner(execution_id, "worker-a", first.fencing_token) is False
    assert leases.is_owner(execution_id, "worker-b", second.fencing_token) is True

    # Journal is deliberately not allowed to become evidence merely because
    # a stale worker still has an old fencing token.
    record = journal.begin("intent-1", execution_id)
    assert record.status in {"prepared", "executing"}
    assert leases.is_owner(execution_id, "worker-a", first.fencing_token) is False
