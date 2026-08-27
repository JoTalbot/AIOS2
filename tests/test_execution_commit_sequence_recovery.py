import json

from runtime.execution_commit import ExecutionCommit, ExecutionCommitCoordinator
from runtime.execution_store import ExecutionStore
from runtime.execution_audit import ExecutionAuditLog


def _coordinator(tmp_path):
    store = ExecutionStore(str(tmp_path / "executions.json"))
    audit = ExecutionAuditLog(str(tmp_path / "audit.jsonl"))
    return ExecutionCommitCoordinator(store, audit, str(tmp_path / "commits.jsonl"))


def _quarantine_records(coordinator):
    if not coordinator.quarantine_path.exists():
        return []
    return [json.loads(line) for line in coordinator.quarantine_path.read_text(encoding="utf-8").splitlines()]


def test_sequence_remains_monotonic_after_quarantined_corruption(tmp_path):
    coordinator = _coordinator(tmp_path)
    first = coordinator._append_journal(ExecutionCommit("c1", "e1", "pending", "running", 0))
    broken = '{"commit_id":"broken","sequence":2,"execution_id":"e1"}'
    with coordinator.journal_path.open("a", encoding="utf-8") as handle:
        handle.write(broken + "\n")
    third = coordinator._append_journal(ExecutionCommit("c3", "e1", "running", "completed", 0))

    assert first.sequence == 1
    assert third.sequence == 3
    assert [commit.sequence for commit in coordinator._read_journal()] == [1, 3]
    quarantine = _quarantine_records(coordinator)
    assert any(record["line"] == broken for record in quarantine)


def test_missing_sequence_is_not_silently_reused(tmp_path):
    coordinator = _coordinator(tmp_path)
    coordinator._append_journal(ExecutionCommit("c1", "e1", "pending", "running", 0))
    broken = '{"commit_id":"gap","execution_id":"e1","from_status":"pending","to_status":"running","attempt":0,"sequence":4,"checksum":"bad"}'
    with coordinator.journal_path.open("a", encoding="utf-8") as handle:
        handle.write(broken + "\n")
    next_commit = coordinator._append_journal(ExecutionCommit("c5", "e1", "pending", "running", 0))

    assert next_commit.sequence == 5
    assert [commit.sequence for commit in coordinator._read_journal()] == [1, 5]
    quarantine = _quarantine_records(coordinator)
    assert any(record["line"] == broken for record in quarantine)
