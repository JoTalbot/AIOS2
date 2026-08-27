from runtime.execution_audit import ExecutionAuditLog
from runtime.execution_commit import ExecutionCommitCoordinator
from runtime.execution_store import ExecutionState, ExecutionStore


def test_reconcile_repairs_pending_commit_after_store_failure(tmp_path, monkeypatch):
    store = ExecutionStore(str(tmp_path / "executions.json"))
    audit = ExecutionAuditLog(str(tmp_path / "audit.jsonl"))
    coordinator = ExecutionCommitCoordinator(
        store,
        audit,
        journal_path=str(tmp_path / "commits.jsonl"),
        quarantine_path=str(tmp_path / "quarantine.jsonl"),
    )
    state = store.save(ExecutionState("exec-1", status="running", attempt=1, correlation_id="corr-1"))

    original_transition = store.transition
    calls = {"count": 0}

    def fail_once(*args, **kwargs):
        calls["count"] += 1
        if calls["count"] == 1:
            raise OSError("simulated crash after journal append")
        return original_transition(*args, **kwargs)

    monkeypatch.setattr(store, "transition", fail_once)
    try:
        coordinator.commit(state, "completed", checkpoint={"ok": True})
    except OSError as exc:
        assert str(exc) == "simulated crash after journal append"

    assert store.get("exec-1").status == "running"
    assert len(coordinator.pending()) == 1

    repaired = coordinator.reconcile()
    assert repaired == ["exec-1:1:completed:corr-1"]
    assert store.get("exec-1").status == "completed"
    assert store.get("exec-1").result == {"ok": True}
    assert coordinator.pending() == []
    assert len(audit.events("exec-1")) == 1


def test_reconcile_does_not_apply_stale_pending_commit_after_concurrent_transition(tmp_path, monkeypatch):
    store = ExecutionStore(str(tmp_path / "executions.json"))
    audit = ExecutionAuditLog(str(tmp_path / "audit.jsonl"))
    coordinator = ExecutionCommitCoordinator(
        store,
        audit,
        journal_path=str(tmp_path / "commits.jsonl"),
        quarantine_path=str(tmp_path / "quarantine.jsonl"),
    )
    state = store.save(ExecutionState("exec-2", status="running", attempt=1, correlation_id="corr-2"))

    original_transition = store.transition
    calls = {"count": 0}

    def fail_once(*args, **kwargs):
        calls["count"] += 1
        if calls["count"] == 1:
            raise OSError("simulated crash after journal append")
        return original_transition(*args, **kwargs)

    monkeypatch.setattr(store, "transition", fail_once)
    try:
        coordinator.commit(state, "completed", checkpoint={"stale": True})
    except OSError as exc:
        assert str(exc) == "simulated crash after journal append"

    pending = coordinator.pending()
    assert len(pending) == 1

    # Another worker legitimately advances the execution before reconciliation.
    store.transition("exec-2", "failed", error="concurrent failure")
    assert store.get("exec-2").status == "failed"

    assert coordinator.reconcile() == []
    assert store.get("exec-2").status == "failed"
    assert store.get("exec-2").error == "concurrent failure"
    assert coordinator.pending() == pending
    assert audit.events("exec-2") == []
