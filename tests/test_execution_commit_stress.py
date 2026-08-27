import threading
import time

from runtime.execution_audit import ExecutionAuditLog
from runtime.execution_commit import ExecutionCommitCoordinator
from runtime.execution_lease import ExecutionLeaseStore
from runtime.execution_store import ExecutionState, ExecutionStore


def test_multi_worker_commit_reconcile_and_lease_rotation_has_bounded_single_outcome(tmp_path):
    leases = ExecutionLeaseStore(str(tmp_path / "leases.json"))
    store = ExecutionStore(str(tmp_path / "executions.json"))
    audit = ExecutionAuditLog(str(tmp_path / "audit.jsonl"))
    state = store.save(ExecutionState("e1", status="running", attempt=1, correlation_id="stress"))
    lease = leases.acquire("e1", "node-a")
    journal = str(tmp_path / "commits.jsonl")
    coordinator = ExecutionCommitCoordinator(store, audit, journal, lease_store=leases, lease_owner_id="node-a", fencing_token=lease.fencing_token)
    barrier = threading.Barrier(3)
    results = []
    errors = []
    results_lock = threading.Lock()

    def record(value):
        with results_lock:
            results.append(value)

    def arrive():
        try:
            barrier.wait(timeout=3)
            return True
        except threading.BrokenBarrierError as exc:
            with results_lock:
                errors.append(exc)
            return False

    def commit_worker():
        if not arrive(): return
        try: record(("commit", coordinator.commit(state, "completed", checkpoint={"ok": True}).commit_id))
        except Exception as exc: record(("commit-error", type(exc).__name__))

    def reconcile_worker():
        if not arrive(): return
        try: record(("reconcile", tuple(coordinator.reconcile())))
        except Exception as exc: record(("reconcile-error", type(exc).__name__))

    def rotation_worker():
        if not arrive(): return
        try:
            released = leases.release("e1", "node-a", lease.fencing_token)
            rotated = leases.acquire("e1", "node-b") if released else None
            record(("rotation", rotated.fencing_token if rotated else None))
        except Exception as exc: record(("rotation-error", type(exc).__name__))

    threads = [
        threading.Thread(target=commit_worker, name="commit-worker", daemon=True),
        threading.Thread(target=reconcile_worker, name="reconcile-worker", daemon=True),
        threading.Thread(target=rotation_worker, name="rotation-worker", daemon=True),
    ]
    deadline = time.monotonic() + 8
    for thread in threads: thread.start()
    for thread in threads:
        remaining = max(0, deadline - time.monotonic())
        thread.join(timeout=remaining)

    assert not errors
    assert all(not thread.is_alive() for thread in threads), "concurrency worker did not terminate"
    assert not any(kind.endswith("-error") for kind, _ in results)
    assert len(results) == 3

    final = store.get("e1")
    events = audit.events("e1")
    assert final is not None
    assert final.status in {"running", "completed"}
    assert len(events) <= 1
    assert len({event.event_id for event in events}) == len(events)

    rotated_tokens = [value for kind, value in results if kind == "rotation" and isinstance(value, int)]
    assert len(rotated_tokens) == 1
    assert rotated_tokens[0] > lease.fencing_token

    winner = ExecutionCommitCoordinator(store, audit, journal, lease_store=leases, lease_owner_id="node-b", fencing_token=rotated_tokens[0])
    winner.reconcile()
    assert store.get("e1").status in {"running", "completed"}
    assert len(audit.events("e1")) <= 1
    assert winner.reconcile() == []
    assert len(audit.events("e1")) <= 1
