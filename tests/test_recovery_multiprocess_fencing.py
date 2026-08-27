"""End-to-end multiprocess lease -> claim -> recovery fencing tests."""
import os
import signal
import subprocess
import sys
import textwrap
import time

from runtime.execution_lease import ExecutionLeaseStore
from runtime.tool_intent_store import ToolIntent, ToolIntentStore


def _env(tmp_path):
    env = os.environ.copy()
    env["PYTHONPATH"] = os.getcwd()
    env["LEASES"] = str(tmp_path / "leases.json")
    env["INTENTS"] = str(tmp_path / "intents.json")
    env["LOCK"] = str(tmp_path / "coord.lock")
    env["MARKER"] = str(tmp_path / "resolver.marker")
    return env


def _wait_marker(path, timeout=8):
    deadline = time.time() + timeout
    while time.time() < deadline:
        if os.path.exists(path):
            return
        time.sleep(0.01)
    raise AssertionError("worker did not reach resolver boundary")


def _start_worker(env, owner):
    code = """
        import os, time
        from runtime.execution_lease import ExecutionLeaseStore
        from runtime.intent_recovery_worker import IntentRecoveryWorker
        from runtime.tool_intent_store import ToolIntentStore
        leases=ExecutionLeaseStore(os.environ['LEASES'], ttl_seconds=1, coordination_lock_path=os.environ['LOCK'])
        intents=ToolIntentStore(os.environ['INTENTS'], claim_ttl_seconds=1, coordination_lock_path=os.environ['LOCK'])
        def resolver(intent):
            open(os.environ['MARKER'], 'w').write(intent.owner_id or 'claimed')
            while True: time.sleep(1)
        w=IntentRecoveryWorker(intents, leases, owner_id=OWNER)
        w.recover_one(intents.get('k'), resolver)
    """.replace("OWNER", repr(owner))
    return subprocess.Popen([sys.executable, "-c", textwrap.dedent(code)], env=env)


def test_old_recovery_worker_cannot_commit_after_takeover(tmp_path):
    env = _env(tmp_path)
    leases = ExecutionLeaseStore(env["LEASES"], ttl_seconds=1, coordination_lock_path=env["LOCK"])
    intents = ToolIntentStore(env["INTENTS"], claim_ttl_seconds=1, coordination_lock_path=env["LOCK"])
    intents.prepare(ToolIntent("k", "call", "send", {}, "e1", "ambiguous"))

    old = _start_worker(env, "old-worker")
    try:
        _wait_marker(env["MARKER"])
        os.kill(old.pid, signal.SIGSTOP)
        time.sleep(1.2)

        # New epoch/owner takes over the execution and intent.
        new_lease = leases.acquire("k", "new-worker")
        assert new_lease is not None
        assert new_lease.fencing_token == 2
        new_claim = intents.claim("k", "new-worker", "recovery:new-worker:2")
        assert new_claim is not None
        assert intents.mark_claimed("k", "new-worker", "recovery:new-worker:2", "completed") is not None

        # Resume the old worker: its lease epoch is stale, so its terminal commit must be rejected.
        os.kill(old.pid, signal.SIGCONT)
        time.sleep(0.3)
        os.kill(old.pid, signal.SIGTERM)
        assert old.wait(timeout=5) != 0

        current = intents.get("k")
        assert current.state == "completed"
        assert current.owner_id is None
        assert current.claim_token is None
    finally:
        if old.poll() is None:
            os.kill(old.pid, signal.SIGKILL)
            old.wait(timeout=5)


def test_kill_after_claim_then_restart_recovery_is_safe(tmp_path):
    env = _env(tmp_path)
    leases = ExecutionLeaseStore(env["LEASES"], ttl_seconds=1, coordination_lock_path=env["LOCK"])
    intents = ToolIntentStore(env["INTENTS"], claim_ttl_seconds=1, coordination_lock_path=env["LOCK"])
    intents.prepare(ToolIntent("k", "call", "send", {}, "e1", "ambiguous"))

    worker = _start_worker(env, "crashed-worker")
    try:
        _wait_marker(env["MARKER"])
        os.kill(worker.pid, signal.SIGKILL)
        assert worker.wait(timeout=5) == -signal.SIGKILL
    finally:
        if worker.poll() is None:
            os.kill(worker.pid, signal.SIGKILL)
            worker.wait(timeout=5)

    time.sleep(1.2)
    new_lease = leases.acquire("k", "restart-worker")
    assert new_lease is not None
    assert new_lease.fencing_token == 2
    claim = intents.claim("k", "restart-worker", "recovery:restart-worker:2")
    assert claim is not None
    assert intents.mark_claimed("k", "restart-worker", "recovery:restart-worker:2", "completed") is not None
    assert intents.get("k").state == "completed"
