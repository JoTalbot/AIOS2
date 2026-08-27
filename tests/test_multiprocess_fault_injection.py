"""Real subprocess crash tests for lease/claim/durable-rename boundaries."""
import json
import os
import signal
import subprocess
import sys
import textwrap
import time

from runtime.execution_lease import ExecutionLeaseStore
from runtime.tool_intent_store import ToolIntent, ToolIntentStore


def _run_killed(code, env):
    proc = subprocess.Popen([sys.executable, "-c", textwrap.dedent(code)], env=env)
    time.sleep(0.25)
    os.kill(proc.pid, signal.SIGKILL)
    assert proc.wait(timeout=5) == -signal.SIGKILL


def _env(tmp_path):
    env = os.environ.copy()
    env["PYTHONPATH"] = os.getcwd()
    env["LEASES"] = str(tmp_path / "leases.json")
    env["INTENTS"] = str(tmp_path / "intents.json")
    return env


def test_sigkill_after_lease_acquire_preserves_fence_for_takeover(tmp_path):
    env = _env(tmp_path)
    _run_killed(
        """
        import os
        from runtime.execution_lease import ExecutionLeaseStore
        s=ExecutionLeaseStore(os.environ['LEASES'], ttl_seconds=1)
        lease=s.acquire('e1','dead-worker')
        assert lease.fencing_token == 1
        os.kill(os.getpid(), 19)
        """,
        env,
    )
    time.sleep(1.1)
    s = ExecutionLeaseStore(env["LEASES"], ttl_seconds=60)
    takeover = s.acquire("e1", "live-worker")
    assert takeover is not None
    assert takeover.fencing_token == 2
    assert not s.is_owner("e1", "dead-worker", 1)


def test_sigkill_after_claim_allows_takeover_without_stale_terminal_write(tmp_path):
    env = _env(tmp_path)
    store = ToolIntentStore(env["INTENTS"], claim_ttl_seconds=1)
    store.prepare(ToolIntent("k", "call", "send", {}, "e1", "ambiguous"))
    _run_killed(
        """
        import os
        from runtime.tool_intent_store import ToolIntentStore
        s=ToolIntentStore(os.environ['INTENTS'], claim_ttl_seconds=1)
        c=s.claim('k','dead-worker','claim-1')
        assert c is not None and c.claim_token == 'claim-1'
        os.kill(os.getpid(), 19)
        """,
        env,
    )
    time.sleep(1.1)
    restarted = ToolIntentStore(env["INTENTS"], claim_ttl_seconds=60)
    assert restarted.claim("k", "live-worker", "claim-2") is not None
    assert restarted.mark_claimed("k", "dead-worker", "claim-1", "completed") is None
    assert restarted.get("k").state == "executing"


def test_sigkill_during_rename_never_leaves_partial_json(tmp_path):
    env = _env(tmp_path)
    _run_killed(
        """
        import os
        from runtime.execution_lease import ExecutionLeaseStore
        s=ExecutionLeaseStore(os.environ['LEASES'])
        original=s._write
        def kill_after_temp(data):
            tmp=s.path.with_suffix(s.path.suffix+'.tmp')
            tmp.write_text('{\\"e1\\": {\\"owner_id\\": \\"crashed\\"}}', encoding='utf-8')
            with tmp.open('r+', encoding='utf-8') as h:
                h.flush(); os.fsync(h.fileno())
            os.kill(os.getpid(), 19)
        s._write=kill_after_temp
        s.acquire('e1','worker')
        """,
        env,
    )
    target = tmp_path / "leases.json"
    assert target.exists()
    data = json.loads(target.read_text(encoding="utf-8"))
    assert isinstance(data, dict)
    assert "e1" not in data
    tmp = tmp_path / "leases.json.tmp"
    assert not tmp.exists()
