"""Crash boundary: durable idempotency result, then SIGKILL before execution commit."""
import os
import signal
import subprocess
import sys
import textwrap
import time

from runtime.execution_audit import ExecutionAuditLog
from runtime.execution_commit import ExecutionCommitCoordinator
from runtime.execution_store import ExecutionState, ExecutionStore
from runtime.tool_idempotency_store import StoredToolResult, ToolIdempotencyStore


def _wait_marker(path, value, timeout=8):
    deadline = time.time() + timeout
    while time.time() < deadline:
        if os.path.exists(path) and open(path, encoding="utf-8").read() == value:
            return
        time.sleep(0.01)
    raise AssertionError(f"marker {value!r} not reached")


def _env(tmp_path):
    env = os.environ.copy()
    env["PYTHONPATH"] = os.getcwd()
    env.update(
        EXECUTIONS=str(tmp_path / "executions.json"),
        IDEM=str(tmp_path / "idempotency.json"),
        AUDIT=str(tmp_path / "audit.jsonl"),
        JOURNAL=str(tmp_path / "commits.jsonl"),
        MARKER=str(tmp_path / "marker"),
    )
    return env


def test_sigkill_after_idempotency_before_execution_commit_reconciles(tmp_path):
    env = _env(tmp_path)
    ExecutionStore(env["EXECUTIONS"]).save(ExecutionState("e1", status="running", attempt=1))
    code = """
import os
from runtime.tool_idempotency_store import StoredToolResult, ToolIdempotencyStore
store = ToolIdempotencyStore(os.environ['IDEM'])
store.put_if_absent(StoredToolResult('op-1', 'call-1', 'external', True, {'value': 42}))
open(os.environ['MARKER'], 'w').write('idempotency-marked')
while True: pass
"""
    proc = subprocess.Popen([sys.executable, "-c", textwrap.dedent(code)], env=env)
    try:
        _wait_marker(env["MARKER"], "idempotency-marked")
        os.kill(proc.pid, signal.SIGKILL)
        assert proc.wait(timeout=5) == -signal.SIGKILL
        idem = ToolIdempotencyStore(env["IDEM"])
        assert idem.get("op-1").value == {"value": 42}
        assert not os.path.exists(env["JOURNAL"])
        store = ExecutionStore(env["EXECUTIONS"])
        audit = ExecutionAuditLog(env["AUDIT"])
        coordinator = ExecutionCommitCoordinator(store, audit, env["JOURNAL"])
        coordinator.commit(store.get("e1"), "completed", checkpoint=idem.get("op-1").value, reason="recovered-idempotency")
        final = store.get("e1")
        assert final.status == "completed"
        assert final.result == {"value": 42}
        assert final.version == 1
        assert len(audit.events("e1")) == 1
        coordinator.commit(final, "completed", checkpoint={"value": 42}, reason="retry")
        assert store.get("e1").version == 1
        assert len(audit.events("e1")) == 1
    finally:
        if proc.poll() is None:
            proc.kill()
            proc.wait(timeout=5)


def test_stale_recovery_cannot_replace_a_winning_execution_commit(tmp_path):
    env = _env(tmp_path)
    store = ExecutionStore(env["EXECUTIONS"])
    store.save(ExecutionState("e1", status="running", attempt=1))
    idem = ToolIdempotencyStore(env["IDEM"])
    idem.put_if_absent(StoredToolResult("op-1", "call-1", "external", True, {"value": 42}))
    audit = ExecutionAuditLog(env["AUDIT"])
    coordinator = ExecutionCommitCoordinator(store, audit, env["JOURNAL"])
    first = store.get("e1")
    coordinator.commit(first, "completed", checkpoint={"winner": True}, reason="winner")
    stale = ExecutionState(**{**first.__dict__, "status": "running", "version": 0})
    coordinator.commit(stale, "completed", checkpoint={"value": 42}, reason="stale-retry")
    assert store.get("e1").result == {"winner": True}
    assert store.get("e1").version == 1
    assert len(audit.events("e1")) == 1
