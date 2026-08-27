import os
import signal
import subprocess
import sys
import textwrap
import time

from runtime.execution_lease import ExecutionLeaseStore
from runtime.tool_intent_store import ToolIntent, ToolIntentStore


def wait_marker(path, value, timeout=8):
    deadline = time.time() + timeout
    while time.time() < deadline:
        if os.path.exists(path) and open(path, encoding="utf-8").read() == value:
            return
        time.sleep(0.01)
    raise AssertionError(f"marker {value!r} not reached")


def test_sigstop_after_claim_takeover_blocks_stale_terminal_commit(tmp_path):
    leases_path = str(tmp_path / "leases.json")
    intents_path = str(tmp_path / "intents.json")
    marker = str(tmp_path / "marker")
    ToolIntentStore(intents_path, claim_ttl_seconds=1).prepare(
        ToolIntent("k", "call", "send", {}, "k", "ambiguous")
    )
    env = os.environ.copy()
    env["PYTHONPATH"] = os.getcwd()
    env.update(LEASES=leases_path, INTENTS=intents_path, MARKER=marker)
    stale_code = textwrap.dedent("""
        import os, signal
        from runtime.execution_lease import ExecutionLeaseStore
        from runtime.tool_intent_store import ToolIntentStore
        leases=ExecutionLeaseStore(os.environ['LEASES'], ttl_seconds=1)
        intents=ToolIntentStore(os.environ['INTENTS'], claim_ttl_seconds=1,
                                coordination_lock_path=leases.lock_path)
        lease=leases.acquire('k','worker-a')
        assert lease is not None
        claim=intents.claim('k','worker-a',f'recovery:worker-a:{lease.fencing_token}')
        assert claim is not None
        open(os.environ['MARKER'],'w').write('claimed')
        os.kill(os.getpid(), signal.SIGSTOP)
        assert not leases.is_owner('k','worker-a',lease.fencing_token)
        assert intents.mark_claimed('k','worker-a',claim.claim_token,'completed') is None
        open(os.environ['MARKER'],'w').write('stale-rejected')
    """)
    stale = subprocess.Popen([sys.executable, "-c", stale_code], env=env)
    try:
        wait_marker(marker, "claimed")
        time.sleep(1.2)
        live_code = textwrap.dedent("""
            import os
            from runtime.execution_lease import ExecutionLeaseStore
            from runtime.tool_intent_store import ToolIntentStore
            from runtime.intent_recovery_worker import IntentRecoveryWorker
            leases=ExecutionLeaseStore(os.environ['LEASES'], ttl_seconds=1)
            intents=ToolIntentStore(os.environ['INTENTS'], claim_ttl_seconds=1,
                                    coordination_lock_path=leases.lock_path)
            result=IntentRecoveryWorker(intents,leases,'worker-b').recover_one(
                intents.get('k'), lambda item: ('completed', {'recovered': True}))
            assert result.status == 'completed', result
            open(os.environ['MARKER'],'w').write('takeover-completed')
        """)
        live = subprocess.run([sys.executable, "-c", live_code], env=env, timeout=8)
        assert live.returncode == 0
        wait_marker(marker, "takeover-completed")
        os.kill(stale.pid, signal.SIGCONT)
        wait_marker(marker, "stale-rejected")
        assert stale.wait(timeout=5) == 0
        final = ToolIntentStore(intents_path).get("k")
        assert final.state == "completed"
        assert final.owner_id is None
        assert final.claim_token is None
    finally:
        if stale.poll() is None:
            stale.kill()
            stale.wait(timeout=5)
