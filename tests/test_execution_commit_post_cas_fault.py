import pytest

from runtime.execution_audit import ExecutionAuditLog
from runtime.execution_commit import ExecutionCommitCoordinator
from runtime.execution_lease import ExecutionLeaseStore
from runtime.execution_store import ExecutionState, ExecutionStore


def test_post_cas_crash_is_recovered_idempotently(tmp_path, monkeypatch):
    leases = ExecutionLeaseStore(str(tmp_path / "leases.json"))
    store = ExecutionStore(str(tmp_path / "executions.json"))
    audit = ExecutionAuditLog(str(tmp_path / "audit.jsonl"))
    state = store.save(ExecutionState("e1", status="running", attempt=1, correlation_id="c1"))
    lease = leases.acquire("e1", "node-a")
    journal = str(tmp_path / "commits.jsonl")
    coordinator = ExecutionCommitCoordinator(store, audit, journal, lease_store=leases, lease_owner_id="node-a", fencing_token=lease.fencing_token)

    original_mark = coordinator._mark
    def crash_before_mark(*args, **kwargs):
        raise RuntimeError("simulated crash after CAS before applied mark")
    monkeypatch.setattr(coordinator, "_mark", crash_before_mark)

    with pytest.raises(RuntimeError, match="after CAS"):
        coordinator.commit(state, "completed", checkpoint={"ok": True})

    assert store.get("e1").status == "completed"
    assert store.get("e1").result == {"ok": True}
    assert audit.events("e1") == []
    assert len(coordinator.pending()) == 1

    monkeypatch.setattr(coordinator, "_mark", original_mark)
    assert coordinator.reconcile() == []
    assert len(coordinator.pending()) == 0
    events = audit.events("e1")
    assert len(events) == 1
    assert events[0].event_id == "e1:1:completed:c1"

    # A second recovery pass is idempotent: no duplicate audit and no state change.
    assert coordinator.reconcile() == []
    assert len(audit.events("e1")) == 1
    assert store.get("e1").version == 2


def test_post_cas_crash_then_lease_rotation_does_not_reapply_stale_intent(tmp_path, monkeypatch):
    leases = ExecutionLeaseStore(str(tmp_path / "leases.json"))
    store = ExecutionStore(str(tmp_path / "executions.json"))
    audit = ExecutionAuditLog(str(tmp_path / "audit.jsonl"))
    state = store.save(ExecutionState("e2", status="running", attempt=1))
    lease = leases.acquire("e2", "node-a")
    journal = str(tmp_path / "commits.jsonl")
    coordinator = ExecutionCommitCoordinator(store, audit, journal, lease_store=leases, lease_owner_id="node-a", fencing_token=lease.fencing_token)

    monkeypatch.setattr(coordinator, "_mark", lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("crash after CAS")))
    with pytest.raises(RuntimeError):
        coordinator.commit(state, "completed", checkpoint={"ok": True})

    assert store.get("e2").status == "completed"
    assert leases.release("e2", "node-a", lease.fencing_token)
    new_lease = leases.acquire("e2", "node-b")

    stale = ExecutionCommitCoordinator(store, audit, journal, lease_store=leases, lease_owner_id="node-a", fencing_token=lease.fencing_token)
    assert stale.reconcile() == []
    assert len(audit.events("e2")) == 0
    assert store.get("e2").status == "completed"
    assert new_lease.fencing_token > lease.fencing_token
