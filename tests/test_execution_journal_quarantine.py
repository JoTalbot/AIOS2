from runtime.execution_audit import ExecutionAuditLog
from runtime.execution_commit import ExecutionCommitCoordinator
from runtime.execution_store import ExecutionStore


def test_corrupt_journal_is_quarantined_under_journal_lock(tmp_path, monkeypatch):
    store = ExecutionStore(str(tmp_path / "executions.json"))
    audit = ExecutionAuditLog(str(tmp_path / "audit.jsonl"))
    journal = tmp_path / "commits.jsonl"
    quarantine = tmp_path / "quarantine.jsonl"
    coordinator = ExecutionCommitCoordinator(
        store,
        audit,
        journal_path=str(journal),
        quarantine_path=str(quarantine),
    )
    journal.write_text("{not-json}\n", encoding="utf-8")

    calls = []

    class ObservedLock:
        def __enter__(self):
            calls.append("enter")
            return self

        def __exit__(self, *args):
            calls.append("exit")
            return False

    monkeypatch.setattr(
        "runtime.execution_commit._JournalLock",
        lambda path: ObservedLock(),
    )

    assert coordinator.pending() == []
    assert calls == ["enter", "exit"]
    records = quarantine.read_text(encoding="utf-8").splitlines()
    assert len(records) == 1
    assert "not-json" in records[0]
