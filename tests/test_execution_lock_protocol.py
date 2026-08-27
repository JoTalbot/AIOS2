import threading

from runtime.execution_audit import ExecutionAuditLog
from runtime.execution_commit import ExecutionCommitCoordinator
from runtime.execution_lease import ExecutionLeaseStore
from runtime.execution_store import ExecutionState, ExecutionStore


def test_coordinator_uses_one_execution_scoped_lock_for_lease_and_state(tmp_path):
    shared = tmp_path / "execution.lock"
    leases = ExecutionLeaseStore(str(tmp_path / "leases.json"), coordination_lock_path=str(shared))
    store = ExecutionStore(str(tmp_path / "executions.json"), coordination_lock_path=str(shared))
    audit = ExecutionAuditLog(str(tmp_path / "audit.jsonl"))
    store.save(ExecutionState("e1", status="running", attempt=1))
    lease = leases.acquire("e1", "node-a")
    coordinator = ExecutionCommitCoordinator(
        store, audit, str(tmp_path / "commits.jsonl"),
        lease_store=leases, lease_owner_id="node-a", fencing_token=lease.fencing_token,
    )

    assert coordinator.store.coordination_lock_path == shared
    assert coordinator.lease_store.lock_path == shared
    coordinator.commit(store.get("e1"), "completed", checkpoint={"ok": True})
    assert store.get("e1").status == "completed"


def test_lease_rotation_waits_for_coordinated_state_transition(tmp_path, monkeypatch):
    shared = tmp_path / "execution.lock"
    leases = ExecutionLeaseStore(str(tmp_path / "leases.json"), coordination_lock_path=str(shared))
    store = ExecutionStore(str(tmp_path / "executions.json"), coordination_lock_path=str(shared))
    audit = ExecutionAuditLog(str(tmp_path / "audit.jsonl"))
    store.save(ExecutionState("e2", status="running", attempt=1))
    old = leases.acquire("e2", "node-a")
    coordinator = ExecutionCommitCoordinator(
        store, audit, str(tmp_path / "commits.jsonl"),
        lease_store=leases, lease_owner_id="node-a", fencing_token=old.fencing_token,
    )

    entered = threading.Event()
    release = threading.Event()
    original_cas = store.compare_and_set

    def blocked_cas(*args, **kwargs):
        entered.set()
        release.wait(timeout=2)
        return original_cas(*args, **kwargs)

    monkeypatch.setattr(store, "compare_and_set", blocked_cas)
    worker = threading.Thread(target=lambda: coordinator.commit(store.get("e2"), "completed"))
    worker.start()
    assert entered.wait(timeout=2)

    rotation_done = threading.Event()
    rotated = []

    def rotate():
        assert leases.release("e2", "node-a", old.fencing_token)
        rotated.append(leases.acquire("e2", "node-b"))
        rotation_done.set()

    rotator = threading.Thread(target=rotate)
    rotator.start()
    assert not rotation_done.wait(timeout=0.1)

    release.set()
    worker.join(timeout=2)
    rotator.join(timeout=2)
    assert rotation_done.is_set()
    assert rotated[0] is not None
    assert store.get("e2").status == "completed"
