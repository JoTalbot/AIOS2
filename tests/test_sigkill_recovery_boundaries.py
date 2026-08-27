"""Hard-crash recovery tests at claim and resolver-return boundaries."""
import os
import signal
import subprocess
import sys
import textwrap
import time

from runtime.execution_lease import ExecutionLeaseStore
from runtime.tool_intent_store import ToolIntent, ToolIntentStore


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
    env["LEASES"] = str(tmp_path / "leases.json")
    env["INTENTS"] = str(tmp_path / "intents.json")
    env["MARKER"] = str(tmp_path / "marker")
    return env


def _start_killable_worker(env, phase):
    code = f"""
import os
from runtime.execution_lease import ExecutionLeaseStore
from runtime.tool_intent_store import ToolIntentStore
from runtime.intent_recovery_worker import IntentRecoveryWorker
leases=ExecutionLeaseStore(os.environ['LEASES'], ttl_seconds=1)
intents=ToolIntentStore(os.environ['INTENTS'], claim_ttl_seconds=1,
                        coordination_lock_path=leases.lock_path)
lease=leases.acquire('k','dead-worker')
assert lease is not None
claim=intents.claim('k','dead-worker',f'recovery:dead-worker:{{lease.fencing_token}}')
assert claim is not None
open(os.environ['MARKER'],'w').write('{phase}')
{('while True: pass' if phase == 'after-claim' else """
def resolver(item):
    result=('completed', {{'resolved': True}})
    open(os.environ['MARKER'],'w').write('resolver-return')
    while True: pass
IntentRecoveryWorker(intents,leases,'dead-worker').recover_one(intents.get('k'), resolver)
""")}
"""
    return subprocess.Popen([sys.executable, "-c", textwrap.dedent(code)], env=env)


def _run_takeover(env):
    code = """
import os
from runtime.execution_lease import ExecutionLeaseStore
from runtime.tool_intent_store import ToolIntentStore
from runtime.intent_recovery_worker import IntentRecoveryWorker
leases=ExecutionLeaseStore(os.environ['LEASES'], ttl_seconds=1)
intents=ToolIntentStore(os.environ['INTENTS'], claim_ttl_seconds=1, coordination_lock_path=leases.lock_path)
result=IntentRecoveryWorker(intents,leases,'live-worker').recover_one(
    intents.get('k'), lambda item: ('completed', {'recovered': True}))
assert result.status == 'completed', result
open(os.environ['MARKER'],'w').write('takeover-completed')
"""
    return subprocess.run([sys.executable, "-c", textwrap.dedent(code)], env=env, timeout=8)


def _exercise(tmp_path, phase, marker_to_kill):
    env = _env(tmp_path)
    ToolIntentStore(env["INTENTS"], claim_ttl_seconds=1).prepare(
        ToolIntent("k", "call", "send", {}, "e1", "ambiguous")
    )
    stale = _start_killable_worker(env, phase)
    try:
        _wait_marker(env["MARKER"], marker_to_kill)
        os.kill(stale.pid, signal.SIGKILL)
        assert stale.wait(timeout=5) == -signal.SIGKILL
        time.sleep(1.2)
        live = _run_takeover(env)
        assert live.returncode == 0
        _wait_marker(env["MARKER"], "takeover-completed")
        final = ToolIntentStore(env["INTENTS"]).get("k")
        assert final.state == "completed"
        assert final.owner_id is None
        assert final.claim_token is None
    finally:
        if stale.poll() is None:
            stale.kill()
            stale.wait(timeout=5)


def test_sigkill_immediately_after_claim_allows_recovery_takeover(tmp_path):
    _exercise(tmp_path, "after-claim", "after-claim")


def test_sigkill_immediately_after_resolver_return_allows_recovery_takeover(tmp_path):
    _exercise(tmp_path, "resolver", "resolver-return")
