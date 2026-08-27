"""Real subprocess crash at the idempotency -> execution-CAS boundary."""
import json
import os
import signal
import subprocess
import sys
import textwrap
import time

from runtime.execution_store import ExecutionStore
from runtime.tool_idempotency_store import StoredToolResult, ToolIdempotencyStore


def _wait_marker(path, value, timeout=8):
    deadline = time.time() + timeout
    while time.time() < deadline:
        if os.path.exists(path) and open(path, encoding="utf-8").read() == value:
            return
        time.sleep(0.01)
    raise AssertionError(f"marker {value!r} not reached")


def test_sigkill_after_idempotency_before_execution_commit_is_recoverable(tmp_path):
    idem = tmp_path / "idempotency.json"
    execution = tmp_path / "execution.json"
    marker = tmp_path / "marker"
    env = os.environ.copy()
    env["PYTHONPATH"] = os.getcwd()
    env.update(IDEM=str(idem), EXECUTION=str(execution), MARKER=str(marker))

    code = """
import os
from runtime.tool_idempotency_store import StoredToolResult, ToolIdempotencyStore
store=ToolIdempotencyStore(os.environ['IDEM'])
assert store.put_if_absent(StoredToolResult('op-1','call-1','external',True,{'ok': True})) is not None
open(os.environ['MARKER'],'w').write('idempotency-committed')
while True: pass
"""
    proc = subprocess.Popen([sys.executable, "-c", textwrap.dedent(code)], env=env)
    try:
        _wait_marker(str(marker), "idempotency-committed")
        os.kill(proc.pid, signal.SIGKILL)
        assert proc.wait(timeout=5) == -signal.SIGKILL

        # The side-effect result is durable, but execution has not committed yet.
        assert ToolIdempotencyStore(str(idem)).get("op-1") is not None
        store = ExecutionStore(str(execution))
        state = store.get("op-1")
        assert state is None

        # Recovery commits exactly once from the durable idempotency result.
        result = store.begin("op-1")
        assert result is not None
        committed = store.commit(
            "op-1", result.version, {"ok": True}, fencing_token=result.fencing_token
        )
        assert committed is True
        final = store.get("op-1")
        assert final.status == "completed"
        assert final.version == result.version + 1
    finally:
        if proc.poll() is None:
            proc.kill()
            proc.wait(timeout=5)


def test_stale_recovery_cannot_overwrite_execution_after_competing_commit(tmp_path):
    execution = tmp_path / "execution.json"
    store = ExecutionStore(str(execution))
    first = store.begin("op-2")
    assert first is not None
    second = store.commit("op-2", first.version, {"winner": "live"}, fencing_token=first.fencing_token)
    assert second is True

    # A stale worker retained the pre-commit version/fence.
    stale = store.commit("op-2", first.version, {"winner": "stale"}, fencing_token=first.fencing_token)
    assert stale is False
    final = store.get("op-2")
    assert final.status == "completed"
    assert final.result == {"winner": "live"}
