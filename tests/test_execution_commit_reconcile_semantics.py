import pytest

from runtime.execution_audit import ExecutionAuditLog
from runtime.execution_commit import ExecutionCommit, ExecutionCommitCoordinator
from runtime.execution_store import ExecutionState, ExecutionStore


def _coordinator(tmp_path):
    store = ExecutionStore(str(tmp_path / "executions.json"))
    audit = ExecutionAuditLog(str(tmp_path / "audit.jsonl"))
    return store, audit, ExecutionCommitCoordinator(store, audit, str(tmp_path / "commits.jsonl"))


def test_reconcile_leaves_obsolete_commit_pending_without_mutating_state(tmp_path):
    store, audit, coordinator = _coordinator(tmp_path)
    store.save(ExecutionState("e1", status="completed", result="winner"))
    coordinator._append_journal(ExecutionCommit("stale", "e1", "pending", "running", 0))

    assert coordinator.reconcile() == []
    assert store.get("e1").status == "completed"
    assert audit.events("e1") == []
    assert [c.commit_id for c in coordinator.pending()] == ["stale"]


def test_reconcile_applies_matching_pending_commit_once(tmp_path):
    store, audit, coordinator = _coordinator(tmp_path)
    store.save(ExecutionState("e1", status="pending"))
    coordinator._append_journal(ExecutionCommit("c1", "e1", "pending", "running", 0))

    assert coordinator.reconcile() == ["c1"]
    assert coordinator.reconcile() == []
    assert store.get("e1").status == "running"
    assert [event.event_id for event in audit.events("e1")] == ["c1"]


@pytest.mark.parametrize("status", ["completed", "failed", "cancelled"])
def test_reconcile_does_not_apply_pending_transition_from_obsolete_state(tmp_path, status):
    store, audit, coordinator = _coordinator(tmp_path)
    store.save(ExecutionState("e1", status=status))
    coordinator._append_journal(ExecutionCommit("c1", "e1", "pending", "running", 0))

    assert coordinator.reconcile() == []
    assert store.get("e1").status == status
    assert audit.events("e1") == []
