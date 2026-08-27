"""End-to-end multiprocess crash/recovery around idempotency and execution CAS."""
import json
import multiprocessing as mp
import os
import signal
import subprocess
import sys
import textwrap
import time

from runtime.execution_audit import ExecutionAuditLog
from runtime.execution_commit import ExecutionCommitCoordinator
from runtime.execution_lease import ExecutionLeaseStore
from runtime.execution_store import ExecutionState, ExecutionStore
from runtime.tool_idempotency_store import StoredToolResult, ToolIdempotencyStore


def _wait_marker(path, value, timeout=10):
    deadline = time.time() + timeout
    while time.time() < deadline:
        if os.path.exists(path) and open(path, encoding="utf-8").read() == value:
            return
        time.sleep(0.01)
    raise AssertionError(f"marker {value!r} not reached")


def _crash_after_idempotency(env):
    code = """
import os
from runtime.tool_idempotency_store import StoredToolResult, ToolIdempotencyStore
store=ToolIdempotencyStore(os.environ['IDEM'])
assert store.put_if_absent(StoredToolResult('op-1','call-1','external',True,{'ok': True})) is not None
open(os.environ['MARKER'],'w').write('idem')
while True: pass
"""
    return subprocess.Popen([sys.executable, "-c", textwrap.dedent(code)], env=env)


def _recovery_worker(root, queue):
    leases = ExecutionLeaseStore(str(root / "leases.json"), ttl_seconds=1)
    store = ExecutionStore(str(root / "executions.json"))
    audit = ExecutionAuditLog(str(root / "audit.jsonl"))
    idem = ToolIdempotencyStore(str(root / "idempotency.json"))
    lease = leases.acquire("e1", f"worker-{os.getpid()}")
    if lease is None:
        queue.put("no-lease")
        return
    try:
        result = idem.get("op-1")
        if result is None:
            queue.put("no-idem")
            return
        state = store.get("e1")
        coordinator = ExecutionCommitCoordinator(
            store, audit, str(root / "commits.jsonl"),
            lease_store=leases, lease_owner_id=f"worker-{os.getpid()}",
            fencing_token=lease.fencing_token,
        )
        commit = coordinator.commit(state, "completed", checkpoint=result.value)
        queue.put(("commit", commit.status, lease.fencing_token))
    finally:
        leases.release("e1", f"worker-{os.getpid()}", lease.fencing_token)


def test_sigkill_after_idempotency_then_16_recovery_workers_have_one_execution_commit(tmp_path):
    root = tmp_path
    leases = ExecutionLeaseStore(str(root / "leases.json"), ttl_seconds=1)
    store = ExecutionStore(str(root / "executions.json"))
    audit = ExecutionAuditLog(str(root / "audit.jsonl"))
    store.save(ExecutionState("e1", status="running", attempt=1, correlation_id="c1"))
    seed = leases.acquire("e1", "seed")
    assert seed is not None
    assert leases.release("e1", "seed", seed.fencing_token)

    env = os.environ.copy()
    env["PYTHONPATH"] = os.getcwd()
    env["IDEM"] = str(root / "idempotency.json")
    env["MARKER"] = str(root / "marker")
    dead = _crash_after_idempotency(env)
    try:
        _wait_marker(env["MARKER"], "idem")
        os.kill(dead.pid, signal.SIGKILL)
        assert dead.wait(timeout=5) == -signal.SIGKILL

        ctx = mp.get_context("spawn")
        queue = ctx.Queue()
        workers = [ctx.Process(target=_recovery_worker, args=(root, queue)) for _ in range(16)]
        for worker in workers:
            worker.start()
        results = [queue.get(timeout=25) for _ in workers]
        for worker in workers:
            worker.join(timeout=10)
            assert worker.exitcode == 0

        committed = [r for r in results if isinstance(r, tuple) and r[0] == "commit"]
        assert committed
        final = ExecutionStore(str(root / "executions.json")).get("e1")
        assert final.status == "completed"
        assert final.version == 2
        events = ExecutionAuditLog(str(root / "audit.jsonl")).events("e1")
        assert len(events) == 1
        assert ToolIdempotencyStore(str(root / "idempotency.json")).get("op-1") is not None
    finally:
        if dead.poll() is None:
            dead.kill()
            dead.wait(timeout=5)


def test_competing_execution_cas_rejects_all_stale_workers(tmp_path):
    root = tmp_path
    leases = ExecutionLeaseStore(str(root / "leases.json"))
    store = ExecutionStore(str(root / "executions.json"))
    audit = ExecutionAuditLog(str(root / "audit.jsonl"))
    store.save(ExecutionState("e2", status="running", attempt=1, correlation_id="c2"))
    lease = leases.acquire("e2", "winner")
    assert lease is not None
    coordinator = ExecutionCommitCoordinator(
        store, audit, str(root / "commits.jsonl"),
        lease_store=leases, lease_owner_id="winner", fencing_token=lease.fencing_token,
    )
    state = store.get("e2")
    assert coordinator.commit(state, "completed", checkpoint={"winner": True}).status == "applied"
    for stale in range(12):
        candidate = ExecutionStore(str(root / "executions.json")).get("e2")
        assert store.compare_and_set(
            ExecutionState(**{**candidate.__dict__, "result": {"stale": stale}}),
            1,
            expected_status="running",
            fencing_token=lease.fencing_token,
            fencing_validator=lambda *_: True,
        ) is False
    final = store.get("e2")
    assert final.result == {"winner": True}
    assert final.version == 2
    assert len(audit.events("e2")) == 1
