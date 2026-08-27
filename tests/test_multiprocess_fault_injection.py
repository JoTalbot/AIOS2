"""Real subprocess crash tests for lock/validation/rename boundaries."""
import json
import os
import signal
import subprocess
import sys
import textwrap
import time

from runtime.execution_lease import ExecutionLeaseStore
from runtime.tool_intent_store import ToolIntent, ToolIntentStore


def _run_to_marker(code, env, marker):
    proc = subprocess.Popen([sys.executable, "-c", textwrap.dedent(code)], env=env)
    deadline = time.time() + 5
    marker_path = env["MARKER"]
    while time.time() < deadline:
        if os.path.exists(marker_path) and open(marker_path, encoding="utf-8").read() == marker:
            os.kill(proc.pid, signal.SIGKILL)
            assert proc.wait(timeout=5) == -signal.SIGKILL
            return
        if proc.poll() is not None:
            raise AssertionError(f"worker exited before marker {marker}: {proc.returncode}")
        time.sleep(0.01)
    os.kill(proc.pid, signal.SIGKILL)
    proc.wait(timeout=5)
    raise AssertionError(f"worker never reached marker {marker}")


def _env(tmp_path):
    env = os.environ.copy()
    env["PYTHONPATH"] = os.getcwd()
    env["LEASES"] = str(tmp_path / "leases.json")
    env["INTENTS"] = str(tmp_path / "intents.json")
    env["MARKER"] = str(tmp_path / "marker")
    return env


def test_sigkill_after_lease_lock_acquisition_is_safe(tmp_path):
    env = _env(tmp_path)
    _run_to_marker(
        """
        import os
        from runtime.execution_lease import ExecutionLeaseStore
        from runtime.execution_lease import _LeaseLock
        class PausingLock(_LeaseLock):
            def __enter__(self):
                result = super().__enter__()
                open(os.environ['MARKER'], 'w').write('locked')
                return result
        s=ExecutionLeaseStore(os.environ['LEASES'])
        s.execution_lock=lambda: PausingLock(s.lock_path)
        s.acquire('e1','dead-worker')
        """,
        env, "locked",
    )
    restarted = ExecutionLeaseStore(env["LEASES"])
    assert restarted.acquire("e1", "live-worker").fencing_token == 1


def test_sigkill_after_lease_validation_before_write_is_safe(tmp_path):
    env = _env(tmp_path)
    _run_to_marker(
        """
        import os
        from runtime.execution_lease import ExecutionLeaseStore
        class PausingStore(ExecutionLeaseStore):
            def _read(self):
                data = super()._read()
                if not os.path.exists(os.environ['MARKER']):
                    open(os.environ['MARKER'], 'w').write('validated')
                    os.kill(os.getpid(), 19)
                return data
        s=PausingStore(os.environ['LEASES'])
        s.acquire('e1','dead-worker')
        """,
        env, "validated",
    )
    restarted = ExecutionLeaseStore(env["LEASES"])
    lease = restarted.acquire("e1", "live-worker")
    assert lease is not None and lease.fencing_token == 1


def test_sigkill_after_lease_fsync_before_rename_preserves_old_target(tmp_path):
    env = _env(tmp_path)
    _run_to_marker(
        """
        import os
        from runtime.execution_lease import ExecutionLeaseStore
        class PausingStore(ExecutionLeaseStore):
            def _write(self, data):
                tmp=self.path.with_suffix(self.path.suffix+'.tmp')
                tmp.write_text(__import__('json').dumps(data), encoding='utf-8')
                with tmp.open('r+', encoding='utf-8') as h:
                    h.flush(); os.fsync(h.fileno())
                open(os.environ['MARKER'], 'w').write('renamed-next')
                os.kill(os.getpid(), 19)
        s=PausingStore(os.environ['LEASES'])
        s.acquire('e1','dead-worker')
        """,
        env, "renamed-next",
    )
    target = tmp_path / "leases.json"
    assert json.loads(target.read_text(encoding="utf-8")) == {}
    assert (tmp_path / "leases.json.tmp").exists()
    # The orphan temp file is harmless; the next writer atomically replaces the target.
    restarted = ExecutionLeaseStore(env["LEASES"])
    assert restarted.acquire("e1", "live-worker").fencing_token == 1


def test_sigkill_after_claim_lock_acquisition_is_safe(tmp_path):
    env = _env(tmp_path)
    store = ToolIntentStore(env["INTENTS"])
    store.prepare(ToolIntent("k", "call", "send", {}, "e1", "ambiguous"))
    _run_to_marker(
        """
        import os
        from runtime.tool_intent_store import ToolIntentStore, _IntentLock
        class PausingLock(_IntentLock):
            def __enter__(self):
                result=super().__enter__()
                open(os.environ['MARKER'],'w').write('locked')
                return result
        s=ToolIntentStore(os.environ['INTENTS'])
        s.execution_lock=lambda: PausingLock(s.lock_path)
        s.claim('k','dead-worker','claim-1')
        """,
        env, "locked",
    )
    restarted = ToolIntentStore(env["INTENTS"])
    claim = restarted.claim("k", "live-worker", "claim-2")
    assert claim is not None
    assert claim.owner_id == "live-worker"


def test_sigkill_after_claim_validation_before_write_is_safe(tmp_path):
    env = _env(tmp_path)
    store = ToolIntentStore(env["INTENTS"])
    store.prepare(ToolIntent("k", "call", "send", {}, "e1", "ambiguous"))
    _run_to_marker(
        """
        import os
        from runtime.tool_intent_store import ToolIntentStore
        class PausingStore(ToolIntentStore):
            def _read(self):
                data=super()._read()
                if not os.path.exists(os.environ['MARKER']):
                    open(os.environ['MARKER'],'w').write('validated')
                    os.kill(os.getpid(), 19)
                return data
        s=PausingStore(os.environ['INTENTS'])
        s.claim('k','dead-worker','claim-1')
        """,
        env, "validated",
    )
    restarted = ToolIntentStore(env["INTENTS"])
    claim = restarted.claim("k", "live-worker", "claim-2")
    assert claim is not None and claim.owner_id == "live-worker"


def test_sigkill_after_claim_fsync_before_rename_preserves_old_target(tmp_path):
    env = _env(tmp_path)
    store = ToolIntentStore(env["INTENTS"])
    store.prepare(ToolIntent("k", "call", "send", {}, "e1", "ambiguous"))
    before = json.loads((tmp_path / "intents.json").read_text(encoding="utf-8"))
    _run_to_marker(
        """
        import json, os
        from runtime.tool_intent_store import ToolIntentStore
        class PausingStore(ToolIntentStore):
            def _write(self, data):
                tmp=self.path.with_suffix(self.path.suffix+'.tmp')
                tmp.write_text(json.dumps(data), encoding='utf-8')
                with tmp.open('r+', encoding='utf-8') as h:
                    h.flush(); os.fsync(h.fileno())
                open(os.environ['MARKER'],'w').write('renamed-next')
                os.kill(os.getpid(), 19)
        s=PausingStore(os.environ['INTENTS'])
        s.claim('k','dead-worker','claim-1')
        """,
        env, "renamed-next",
    )
    assert json.loads((tmp_path / "intents.json").read_text(encoding="utf-8")) == before
    restarted = ToolIntentStore(env["INTENTS"])
    assert restarted.get("k").owner_id is None
    assert restarted.claim("k", "live-worker", "claim-2") is not None
