from runtime.execution_audit import ExecutionAuditLog
from runtime.execution_commit import ExecutionCommit, ExecutionCommitCoordinator
from runtime.execution_lease import ExecutionLeaseStore
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
    coordinator = ExecutionCommitCoordinator(store, audit, journal_path=str(tmp_path / "commits.jsonl"), quarantine_path=str(tmp_path / "quarantine.jsonl"))
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
    store.transition("exec-2", "failed", error="concurrent failure")
    assert coordinator.reconcile() == []
    assert store.get("exec-2").status == "failed"
    assert store.get("exec-2").error == "concurrent failure"
    assert coordinator.pending() == pending
    assert audit.events("exec-2") == []


def test_reconcile_skips_pending_commit_when_fencing_token_is_stale(tmp_path):
    lease_store = ExecutionLeaseStore(str(tmp_path / "leases.json"))
    store = ExecutionStore(str(tmp_path / "executions.json"))
    audit = ExecutionAuditLog(str(tmp_path / "audit.jsonl"))
    store.save(ExecutionState("exec-3", status="running", attempt=1, correlation_id="corr-3"))

    old_lease = lease_store.acquire("exec-3", "node-a")
    coordinator = ExecutionCommitCoordinator(
        store, audit,
        journal_path=str(tmp_path / "commits.jsonl"),
        quarantine_path=str(tmp_path / "quarantine.jsonl"),
        lease_store=lease_store, lease_owner_id="node-a", fencing_token=old_lease.fencing_token,
    )
    coordinator._append_journal(ExecutionCommit(
        "exec-3:1:completed:corr-3", "exec-3", "running", "completed", 1,
        {"stale": True}, correlation_id="corr-3",
    ))

    assert lease_store.release("exec-3", "node-a", old_lease.fencing_token) is True
    new_lease = lease_store.acquire("exec-3", "node-b")
    assert new_lease.fencing_token > old_lease.fencing_token
    assert coordinator.reconcile() == []
    assert store.get("exec-3").status == "running"
    assert coordinator.pending()
    assert audit.events("exec-3") == []


def test_commit_leaves_pending_intent_when_fencing_is_lost_after_journal_append(tmp_path, monkeypatch):
    lease_store = ExecutionLeaseStore(str(tmp_path / "leases.json"))
    store = ExecutionStore(str(tmp_path / "executions.json"))
    audit = ExecutionAuditLog(str(tmp_path / "audit.jsonl"))
    state = store.save(ExecutionState("exec-4", status="running", attempt=1, correlation_id="corr-4"))
    lease = lease_store.acquire("exec-4", "node-a")
    coordinator = ExecutionCommitCoordinator(
        store, audit,
        journal_path=str(tmp_path / "commits.jsonl"),
        quarantine_path=str(tmp_path / "quarantine.jsonl"),
        lease_store=lease_store, lease_owner_id="node-a", fencing_token=lease.fencing_token,
    )

    calls = {"count": 0}
    original_is_owner = lease_store.is_owner

    def lose_fence(*args, **kwargs):
        calls["count"] += 1
        if calls["count"] == 2:
            return False
        return original_is_owner(*args, **kwargs)

    monkeypatch.setattr(lease_store, "is_owner", lose_fence)
    pending = coordinator.commit(state, "completed", checkpoint={"fenced": True})
    assert pending.status == "pending"
    assert store.get("exec-4").status == "running"
    assert coordinator.pending()[0].commit_id == pending.commit_id
    assert audit.events("exec-4") == []
