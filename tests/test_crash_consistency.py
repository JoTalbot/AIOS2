import pytest

from runtime.execution_audit import ExecutionAuditLog
from runtime.execution_commit import ExecutionCommitCoordinator
from runtime.execution_store import ExecutionState, ExecutionStore


def _coordinator(tmp_path):
    store = ExecutionStore(str(tmp_path / "executions.json"))
    audit = ExecutionAuditLog(str(tmp_path / "audit.jsonl"))
    coordinator = ExecutionCommitCoordinator(
        store,
        audit,
        str(tmp_path / "commits.jsonl"),
        str(tmp_path / "quarantine.jsonl"),
    )
    return store, audit, coordinator


def test_crash_after_journal_append_reconciles_exactly_once(tmp_path, monkeypatch):
    store, audit, coordinator = _coordinator(tmp_path)
    store.save(ExecutionState("e1", status="pending"))

    original_transition = store.transition
    crashed = {"value": False}

    def crash_once(*args, **kwargs):
        if not crashed["value"]:
            crashed["value"] = True
            raise RuntimeError("simulated worker crash")
        return original_transition(*args, **kwargs)

    monkeypatch.setattr(store, "transition", crash_once)
    with pytest.raises(RuntimeError, match="simulated worker crash"):
        coordinator.commit(store.get("e1"), "running", reason="worker-start")

    assert store.get("e1").status == "pending"
    assert len(coordinator.pending()) == 1

    monkeypatch.setattr(store, "transition", original_transition)
    assert coordinator.reconcile() == [coordinator.pending(all_statuses=True)[0].commit_id]
    assert store.get("e1").status == "running"
    assert len(audit.events("e1")) == 1

    # A second recovery pass must not duplicate the lifecycle audit.
    assert coordinator.reconcile() == []
    assert len(audit.events("e1")) == 1


def test_crash_after_store_before_audit_is_reconciled_without_duplicate_state(tmp_path, monkeypatch):
    store, audit, coordinator = _coordinator(tmp_path)
    store.save(ExecutionState("e2", status="pending"))

    original_audit = audit.append
    failed = {"value": False}

    def crash_audit(event):
        if not failed["value"]:
            failed["value"] = True
            raise RuntimeError("simulated audit crash")
        return original_audit(event)

    monkeypatch.setattr(audit, "append", crash_audit)
    with pytest.raises(RuntimeError, match="simulated audit crash"):
        coordinator.commit(store.get("e2"), "running", reason="worker-start")

    assert store.get("e2").status == "running"
    assert len(coordinator.pending()) == 1

    monkeypatch.setattr(audit, "append", original_audit)
    # Reconciliation observes the already-applied state and repairs only the
    # missing audit/terminal journal marker.
    assert coordinator.reconcile() == [coordinator.pending(all_statuses=True)[0].commit_id]
    assert len(audit.events("e2")) == 1
    assert coordinator.reconcile() == []
