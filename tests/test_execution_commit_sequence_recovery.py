from runtime.execution_commit import ExecutionCommit, ExecutionCommitCoordinator
from runtime.execution_store import ExecutionStore
from runtime.execution_audit import ExecutionAuditLog


def _coordinator(tmp_path):
    store = ExecutionStore(str(tmp_path / "executions.json"))
    audit = ExecutionAuditLog(str(tmp_path / "audit.jsonl"))
    return ExecutionCommitCoordinator(store, audit, str(tmp_path / "commits.jsonl"))


def test_sequence_remains_monotonic_after_quarantined_corruption(tmp_path):
    coordinator = _coordinator(tmp_path)
    first = coordinator._append_journal(ExecutionCommit("c1", "e1", "pending", "running", 0))
    with coordinator.journal_path.open("a", encoding="utf-8") as handle:
        handle.write('{"commit_id":"broken","sequence":2,"execution_id":"e1"}\n')
    third = coordinator._append_journal(ExecutionCommit("c3", "e1", "running", "completed", 0))

    assert first.sequence == 1
    assert third.sequence == 3
    commits = coordinator._read_journal()
    assert [commit.sequence for commit in commits] == [1, 3]
    assert len(coordinator.quarantine_path.read_text(encoding="utf-8").splitlines()) == 1


def test_missing_sequence_is_not_silently_reused(tmp_path):
    coordinator = _coordinator(tmp_path)
    coordinator._append_journal(ExecutionCommit("c1", "e1", "pending", "running", 0))
    with coordinator.journal_path.open("a", encoding="utf-8") as handle:
        handle.write('{"commit_id":"gap","execution_id":"e1","from_status":"pending","to_status":"running","attempt":0,"sequence":4,"checksum":"bad"}\n')
    next_commit = coordinator._append_journal(ExecutionCommit("c5", "e1", "pending", "running", 0))

    assert next_commit.sequence == 5
    assert [commit.sequence for commit in coordinator._read_journal()] == [1]
