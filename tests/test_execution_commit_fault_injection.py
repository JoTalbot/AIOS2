import pytest

from runtime.execution_audit import ExecutionAuditLog
from runtime.execution_commit import ExecutionCommitCoordinator
from runtime.execution_lease import ExecutionLeaseStore
from runtime.execution_store import ExecutionState, ExecutionStore


def test_fault_inside_shared_lock_leaves_pending_intent_and_durable_state(tmp_path, monkeypatch):
    leases = ExecutionLeaseStore(str(tmp_path / "leases.json"))
    store = ExecutionStore(str(tmp_path / "executions.json"))
    audit = ExecutionAuditLog(str(tmp_path / "audit.jsonl"))
    state = store.save(ExecutionState("e1", status="running", attempt=1))
    lease = leases.acquire("e1", "node-a")
    coordinator = ExecutionCommitCoordinator(store, audit, str(tmp_path / "commits.jsonl"), lease_store=leases, lease_owner_id="node-a", fencing_token=lease.fencing_token)

    original_cas = store.compare_and_set
    def crash_after_validation(*args, **kwargs):
        raise RuntimeError("simulated crash inside coordinated critical section")
    monkeypatch.setattr(store, "compare_and_set", crash_after_validation)

    with pytest.raises(RuntimeError, match="simulated crash"):
        coordinator.commit(state, "completed", checkpoint={"ok": True})

    assert store.get("e1").status == "running"
    assert audit.events("e1") == []
    assert len(coordinator.pending()) == 1
    assert leases.is_owner("e1", "node-a", lease.fencing_token)


def test_lease_rotation_cannot_interleave_with_faulted_state_cas(tmp_path, monkeypatch):
    leases = ExecutionLeaseStore(str(tmp_path / "leases.json"))
    store = ExecutionStore(str(tmp_path / "executions.json"))
    audit = ExecutionAuditLog(str(tmp_path / "audit.jsonl"))
    state = store.save(ExecutionState("e2", status="running", attempt=1))
    lease = leases.acquire("e2", "node-a")
    coordinator = ExecutionCommitCoordinator(store, audit, str(tmp_path / "commits.jsonl"), lease_store=leases, lease_owner_id="node-a", fencing_token=lease.fencing_token)

    entered = {"value": False}
    def faulting_cas(*args, **kwargs):
        entered["value"] = True
        raise RuntimeError("crash before state CAS")
    monkeypatch.setattr(store, "compare_and_set", faulting_cas)

    with pytest.raises(RuntimeError):
        coordinator.commit(state, "completed", checkpoint={"ok": True})

    assert entered["value"]
    # The shared lock has been released by the exception; the old lease remains
    # valid, and a new owner can rotate the fencing token only after the failed
    # critical section has exited.
    assert leases.is_owner("e2", "node-a", lease.fencing_token)
    assert leases.release("e2", "node-a", lease.fencing_token)
    rotated = leases.acquire("e2", "node-b")
    assert rotated is not None
    assert rotated.fencing_token > lease.fencing_token
