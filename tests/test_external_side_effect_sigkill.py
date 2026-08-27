"""Crash after an external side effect but before durable idempotency/commit mark."""
import json
import os
import signal
import subprocess
import sys
import textwrap
import time


def _wait(path, value, timeout=8):
    deadline = time.time() + timeout
    while time.time() < deadline:
        if os.path.exists(path) and open(path, encoding="utf-8").read() == value:
            return
        time.sleep(0.01)
    raise AssertionError(f"marker {value!r} not reached")


def test_sigkill_after_external_side_effect_before_idempotency_mark(tmp_path):
    root = tmp_path
    marker = root / "marker"
    effects = root / "effects.json"
    idem = root / "idempotency.json"
    env = os.environ.copy()
    env["PYTHONPATH"] = os.getcwd()
    env.update(MARKER=str(marker), EFFECTS=str(effects), IDEM=str(idem))
    code = """
import json, os
from pathlib import Path
from runtime.tool_idempotency_store import StoredToolResult, ToolIdempotencyStore

key='op-1'
effects=Path(os.environ['EFFECTS'])
data=json.loads(effects.read_text()) if effects.exists() else {'count': 0}
# Simulated external side effect: deliberately outside the idempotency store.
data['count'] += 1
effects.write_text(json.dumps(data))
open(os.environ['MARKER'],'w').write('side-effect')
while True: pass
"""
    proc = subprocess.Popen([sys.executable, "-c", textwrap.dedent(code)], env=env)
    try:
        _wait(str(marker), "side-effect")
        os.kill(proc.pid, signal.SIGKILL)
        assert proc.wait(timeout=5) == -signal.SIGKILL

        # Recovery must observe that the side effect is ambiguous, not replay it.
        recovered = json.loads(effects.read_text())
        assert recovered["count"] == 1
        assert not idem.exists()

        # A resolver/reconciler records the already-observed effect exactly once.
        ToolIdempotencyStore(str(idem)).put_if_absent(
            StoredToolResult(key, "call-1", "external", True, {"recovered": True})
        )
        assert ToolIdempotencyStore(str(idem)).get(key).value == {"recovered": True}

        # Re-running recovery is idempotent and must not invoke the external effect.
        stored = ToolIdempotencyStore(str(idem)).get(key)
        assert stored is not None
        assert json.loads(effects.read_text())["count"] == 1
    finally:
        if proc.poll() is None:
            proc.kill()
            proc.wait(timeout=5)


def test_sigkill_after_side_effect_does_not_allow_stale_worker_to_mark_commit(tmp_path):
    root = tmp_path
    marker = root / "marker"
    effects = root / "effects.json"
    idem = root / "idempotency.json"
    env = os.environ.copy()
    env["PYTHONPATH"] = os.getcwd()
    env.update(MARKER=str(marker), EFFECTS=str(effects), IDEM=str(idem))
    code = """
import json, os
from pathlib import Path
p=Path(os.environ['EFFECTS'])
p.write_text(json.dumps({'count': 1, 'owner': 'stale'}))
open(os.environ['MARKER'],'w').write('side-effect')
while True: pass
"""
    proc = subprocess.Popen([sys.executable, "-c", textwrap.dedent(code)], env=env)
    try:
        _wait(str(marker), "side-effect")
        os.kill(proc.pid, signal.SIGKILL)
        assert proc.wait(timeout=5) == -signal.SIGKILL
        # No commit marker was written by the dead worker.
        assert not idem.exists()
        # Recovery records the effect; the stale owner is not authoritative.
        ToolIdempotencyStore = __import__('runtime.tool_idempotency_store', fromlist=['ToolIdempotencyStore']).ToolIdempotencyStore
        StoredToolResult = __import__('runtime.tool_idempotency_store', fromlist=['StoredToolResult']).StoredToolResult
        store = ToolIdempotencyStore(str(idem))
        store.put_if_absent(StoredToolResult('op-2', 'call-2', 'external', True, {'reconciled': True}))
        assert store.get('op-2').value == {'reconciled': True}
        assert json.loads(effects.read_text())['count'] == 1
    finally:
        if proc.poll() is None:
            proc.kill()
            proc.wait(timeout=5)
