import dataclasses
import json

from runtime.execution_audit import ExecutionAuditLog
from runtime.execution_commit import ExecutionCommit, ExecutionCommitCoordinator
from runtime.execution_store import ExecutionState, ExecutionStore


def test_commit_persists_state_and_audit(tmp_path):
    store = ExecutionStore(str(tmp_path / "executions.json"))
    audit = ExecutionAuditLog(str(tmp_path / "audit.jsonl"))
    coordinator = ExecutionCommitCoordinator(store, audit, str(tmp_path / "commits.jsonl"))
    store.save(ExecutionState("e1", status="pending", correlation_id="corr-1"))
    coordinator.commit(store.get("e1"), "running", reason="worker-start")
    assert store.get("e1").status == "running"
    assert len(audit.events("e1")) == 1


def test_reconcile_repairs_interrupted_commit(tmp_path):
    store = ExecutionStore(str(tmp_path / "executions.json"))
    audit = ExecutionAuditLog(str(tmp_path / "audit.jsonl"))
    coordinator = ExecutionCommitCoordinator(store, audit, str(tmp_path / "commits.jsonl"))
    store.save(ExecutionState("e1", status="pending"))
    coordinator._append_journal(ExecutionCommit("c1", "e1", "pending", "running", 0, reason="crash"))
    repaired = coordinator.reconcile()
    assert repaired == ["c1"]
    assert store.get("e1").status == "running"
    assert audit.events("e1")[0].event_id == "c1"


def test_corrupt_line_does_not_poison_following_valid_sequence(tmp_path):
    store = ExecutionStore(str(tmp_path / "executions.json"))
    audit = ExecutionAuditLog(str(tmp_path / "audit.jsonl"))
    journal = tmp_path / "commits.jsonl"
    coordinator = ExecutionCommitCoordinator(store, audit, str(journal))

    first = ExecutionCommit("c1", "e1", "pending", "running", 0).with_integrity()
    second = ExecutionCommit("c2", "e1", "running", "completed", 0, sequence=2).with_integrity()
    journal.write_text(
        "{malformed}\n" + json.dumps(dataclasses.asdict(second)) + "\n",
        encoding="utf-8",
    )

    commits = coordinator.pending(all_statuses=True)
    assert [commit.commit_id for commit in commits] == ["c2"]
    appended = coordinator._append_journal(first)
    assert appended.sequence == 3
    assert len(coordinator.pending(all_statuses=True)) == 2
