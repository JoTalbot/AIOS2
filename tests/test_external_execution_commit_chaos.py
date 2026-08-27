"""End-to-end crash boundary: external effect -> idempotency -> execution CAS."""
import json
import multiprocessing as mp
import os
import signal
import subprocess
import sys
import textwrap
import time

from runtime.execution_commit import ExecutionCommitCoordinator
from runtime.execution_store import ExecutionState, ExecutionStore
from runtime.execution_audit import ExecutionAuditLog
from runtime.execution_lease import ExecutionLeaseStore
from runtime.tool_idempotency_store import StoredToolResult, ToolIdempotencyStore


def _wait_marker(path, value, timeout=8):
    deadline = time.time() + timeout
    while time.time() < deadline:
        if os.path.exists(path) and open(path, encoding="utf-8").read() == value:
            return
        time.sleep(0.01)
    raise AssertionError(f"marker {value!r} not reached")


def _crash_after_effect(env):
    code = """
import json, os
from pathlib import Path
p=Path(os.environ['EFFECTS'])
p.write_text(json.dumps({'count': 1, 'idempotency_key': 'op-1', 'result': {'ok': True}}))
Path(os.environ['MARKER']).write_text('effect-done')
while True: pass
"""
    return subprocess.Popen([sys.executable, "-c", textwrap.dedent(code)], env=env)


def _recover(env, owner):
    code = """
import json, os
from runtime.execution_commit import ExecutionCommitCoordinator
from runtime.execution_lease import ExecutionLeaseStore
from runtime.execution_store import ExecutionStore
from runtime.execution_audit import ExecutionAuditLog
from runtime.tool_idempotency_store import ToolIdempotencyStore, StoredToolResult
leases=ExecutionLeaseStore(os.environ['LEASES'], ttl_seconds=1)
store=ExecutionStore(os.environ['EXECUTIONS'], coordination_lock_path=leases.lock_path)
audit=ExecutionAuditLog(os.environ['AUDIT'])
idem=ToolIdempotencyStore(os.environ['IDEM'])
lease=leases.acquire('e1', os.environ['OWNER'])
assert lease is not None
effect=json.loads(open(os.environ['EFFECTS']).read())
assert effect['count'] == 1
if idem.get('op-1') is None:
    idem.put_if_absent(StoredToolResult('op-1','call-1','external',True,effect['result']))
coordinator=ExecutionCommitCoordinator(store,audit,os.environ['COMMITS'],lease_store=leases,lease_owner_id=os.environ['OWNER'],fencing_token=lease.fencing_token)
coordinator.commit(store.get('e1'),'completed',checkpoint=effect['result'])
"""
    child_env = dict(env)
    child_env["OWNER"] = owner
    return subprocess.run([sys.executable, "-c", textwrap.dedent(code)], env=child_env, timeout=8)


def _env(tmp_path):
    env = os.environ.copy()
    env["PYTHONPATH"] = os.getcwd()
    for key, name in {
        "EFFECTS":"effects.json", "IDEM":"idempotency.json", "EXECUTIONS":"executions.json",
        "LEASES":"leases.json", "AUDIT":"audit.jsonl", "COMMITS":"commits.jsonl", "MARKER":"marker",
    }.items():
        env[key] = str(tmp_path / name)
    return env


def test_sigkill_after_effect_then_recovery_commits_without_reexecution(tmp_path):
    env = _env(tmp_path)
    ExecutionStore(env["EXECUTIONS"], coordination_lock_path=env["LEASES"]).save(
        ExecutionState("e1", status="running", attempt=1, correlation_id="c1")
    )
    dead = _crash_after_effect(env)
    try:
        _wait_marker(env["MARKER"], "effect-done")
        os.kill(dead.pid, signal.SIGKILL)
        assert dead.wait(timeout=5) == -signal.SIGKILL
        assert json.loads(open(env["EFFECTS"]).read())["count"] == 1
        assert not os.path.exists(env["IDEM"])
        assert _recover(env, "recovery-a").returncode == 0
        assert json.loads(open(env["EFFECTS"]).read())["count"] == 1
        assert ToolIdempotencyStore(env["IDEM"]).get("op-1") is not None
        assert ExecutionStore(env["EXECUTIONS"], coordination_lock_path=env["LEASES"]).get("e1").status == "completed"
    finally:
        if dead.poll() is None:
            dead.kill()
            dead.wait(timeout=5)


def _concurrent_reconcile(env, barrier, queue, owner):
    barrier.wait()
    result = _recover(env, owner)
    queue.put(result.returncode)


def test_concurrent_recovery_after_effect_preserves_single_commit(tmp_path):
    env = _env(tmp_path)
    ExecutionStore(env["EXECUTIONS"], coordination_lock_path=env["LEASES"]).save(
        ExecutionState("e1", status="running", attempt=1, correlation_id="c1")
    )
    open(env["EFFECTS"], "w", encoding="utf-8").write(json.dumps({"count":1,"idempotency_key":"op-1","result":{"ok":True}}))
    ctx = mp.get_context("spawn")
    barrier, queue = ctx.Barrier(4), ctx.Queue()
    workers = [ctx.Process(target=_concurrent_reconcile, args=(env, barrier, queue, f"recovery-{i}")) for i in range(4)]
    for worker in workers: worker.start()
    codes = [queue.get(timeout=20) for _ in workers]
    for worker in workers:
        worker.join(timeout=10)
        assert worker.exitcode == 0
    assert all(code == 0 for code in codes)
    assert ToolIdempotencyStore(env["IDEM"]).get("op-1") is not None
    assert json.loads(open(env["EFFECTS"]).read())["count"] == 1
    final = ExecutionStore(env["EXECUTIONS"], coordination_lock_path=env["LEASES"]).get("e1")
    assert final.status == "completed"
    assert final.version == 1
