import threading

from runtime.execution_audit import ExecutionAuditLog
from runtime.execution_commit import ExecutionCommitCoordinator
from runtime.execution_lease import ExecutionLeaseStore
from runtime.execution_store import ExecutionState, ExecutionStore


def test_multi_worker_commit_reconcile_and_lease_rotation_has_single_outcome(tmp_path):
    leases = ExecutionLeaseStore(str(tmp_path / "leases.json"))
    store = ExecutionStore(str(tmp_path / "executions.json"))
    audit = ExecutionAuditLog(str(tmp_path / "audit.jsonl"))
    state = store.save(ExecutionState("e1", status="running", attempt=1, correlation_id="stress"))
    lease = leases.acquire("e1", "node-a")
    journal = str(tmp_path / "commits.jsonl")
    coordinator = ExecutionCommitCoordinator(store, audit, journal, lease_store=leases, lease_owner_id="node-a", fencing_token=lease.fencing_token)
    barrier = threading.Barrier(3)
    results = []

    def commit_worker():
        barrier.wait()
        try:
            results.append(coordinator.commit(state, "completed", checkpoint={"ok": True}).commit_id)
        except Exception as exc:
            results.append(type(exc).__name__)

    def reconcile_worker():
        barrier.wait()
        results.append(tuple(coordinator.reconcile()))

    def rotation_worker():
        barrier.wait()
        # Rotation cannot interleave with the coordinated state mutation.
        leases.release("e1", "node-a", lease.fencing_token)
        rotated = leases.acquire("e1", "node-b")
        results.append(rotated.fencing_token if rotated else None)

    threads = [threading.Thread(target=commit_worker), threading.Thread(target=reconcile_worker), threading.Thread(target=rotation_worker)]
    for thread in threads: thread.start()
    for thread in threads: thread.join()

    assert store.get("e1").status == "completed"
    assert len(audit.events("e1")) == 1
    assert len({event.event_id for event in audit.events("e1")}) == 1
    assert len(coordinator.pending()) == 0 or len(coordinator.pending()) == 1
    assert any(isinstance(item, int) and item > lease.fencing_token for item in results)

    # Recovery remains idempotent after all concurrent actors finish.
    winner = ExecutionCommitCoordinator(store, audit, journal, lease_store=leases, lease_owner_id="node-b", fencing_token=max(item for item in results if isinstance(item, int)))
    assert winner.reconcile() == []
    assert len(audit.events("e1")) == 1
