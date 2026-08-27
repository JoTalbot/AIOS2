"""Real subprocess SIGKILL tests for lease/claim/durable-rename boundaries."""
import json
import os
import signal
import subprocess
import sys
import time

import pytest

from runtime.tool_intent_store import ToolIntent, ToolIntentStore
from runtime.execution_lease import ExecutionLeaseStore


pytestmark = pytest.mark.skipif(os.name != "posix", reason="requires POSIX SIGKILL/fcntl semantics")


def _run_until_marker(code, env, marker):
    proc = subprocess.Popen([sys.executable, "-c", code], env=env)
    deadline = time.monotonic() + 5
    marker_path = env["MARKER"]
    while time.monotonic() < deadline:
        if os.path.exists(marker_path):
            os.kill(proc.pid, signal.SIGKILL)
            assert proc.wait(timeout=5) == -signal.SIGKILL
            return
        if proc.poll() is not None:
            raise AssertionError(f"child exited before {marker}: {proc.returncode}")
        time.sleep(0.01)
    os.kill(proc.pid, signal.SIGKILL)
    proc.wait(timeout=5)
    raise AssertionError(f"child never reached {marker}")


def _env(tmp_path):
    env = os.environ.copy()
    env["PYTHONPATH"] = os.getcwd()
    env["LEASES"] = str(tmp_path / "leases.json")
    env["INTENTS"] = str(tmp_path / "intents.json")
    env["MARKER"] = str(tmp_path / "reached")
    return env


def test_sigkill_after_lease_acquire_preserves_fence_for_takeover(tmp_path):
    env = _env(tmp_path)
    _run_until_marker(
        """import os
from runtime.execution_lease import ExecutionLeaseStore
s=ExecutionLeaseStore(os.environ['LEASES'], ttl_seconds=1)
lease=s.acquire('e1','dead-worker')
assert lease.fencing_token == 1
open(os.environ['MARKER'],'w').close()
while True: pass
""",
        env,
        "lease acquisition",
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
    _run_until_marker(
        """import os
from runtime.tool_intent_store import ToolIntentStore
s=ToolIntentStore(os.environ['INTENTS'], claim_ttl_seconds=1)
c=s.claim('k','dead-worker','claim-1')
assert c is not None and c.claim_token == 'claim-1'
open(os.environ['MARKER'],'w').close()
while True: pass
""",
        env,
        "claim acquisition",
    )
    time.sleep(1.1)
    restarted = ToolIntentStore(env["INTENTS"], claim_ttl_seconds=60)
    assert restarted.claim("k", "live-worker", "claim-2") is not None
    assert restarted.mark_claimed("k", "dead-worker", "claim-1", "completed") is None
    assert restarted.get("k").state == "executing"


def test_sigkill_after_durable_temp_write_never_exposes_partial_target(tmp_path):
    env = _env(tmp_path)
    _run_until_marker(
        """import os
from runtime.execution_lease import ExecutionLeaseStore
s=ExecutionLeaseStore(os.environ['LEASES'])
tmp=s.path.with_suffix(s.path.suffix+'.tmp')
tmp.write_text('{\\"e1\\": {\\"owner_id\\": \\"crashed\\"}}', encoding='utf-8')
with tmp.open('r+', encoding='utf-8') as h:
    h.flush()
    os.fsync(h.fileno())
open(os.environ['MARKER'],'w').close()
while True: pass
""",
        env,
        "durable temp-file write",
    )
    target = tmp_path / "leases.json"
    assert not target.exists()
    assert json.loads((tmp_path / "leases.json.tmp").read_text(encoding="utf-8"))["e1"]["owner_id"] == "crashed"
    # A restart can safely initialize the target; the orphan temp file is not
    # treated as authoritative state.
    restarted = ExecutionLeaseStore(env["LEASES"])
    assert json.loads(target.read_text(encoding="utf-8")) == {}
