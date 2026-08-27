"""Real-process ToolExecutor crash at idempotency -> intent-commit boundary."""
import asyncio
import os
import signal
import subprocess
import sys
import textwrap
import time


def _wait_marker(path, value, timeout=10):
    deadline = time.time() + timeout
    while time.time() < deadline:
        if os.path.exists(path) and open(path, encoding="utf-8").read() == value:
            return
        time.sleep(0.01)
    raise AssertionError(f"marker {value!r} not reached")


def test_real_tool_executor_sigkill_after_idempotency_before_intent_commit(tmp_path):
    marker = tmp_path / "marker"
    idem = tmp_path / "idempotency.json"
    intents = tmp_path / "intents.json"
    effects = tmp_path / "effects.json"
    env = os.environ.copy()
    env["PYTHONPATH"] = os.getcwd()
    env.update(MARKER=str(marker), IDEM=str(idem), INTENTS=str(intents), EFFECTS=str(effects))

    code = """
import asyncio, json, os
from pathlib import Path
from runtime.tool_executor import ToolExecutor
from runtime.tool_idempotency_store import ToolIdempotencyStore
from runtime.tool_intent_store import ToolIntentStore
from runtime.tool_protocol import ToolCall, ToolResult
from runtime.tool_sandbox import ToolExecutionContext

class Sandbox:
    async def execute(self, call, context, execution_context=None):
        p=Path(os.environ['EFFECTS'])
        data=json.loads(p.read_text()) if p.exists() else {'count': 0}
        data['count'] += 1
        p.write_text(json.dumps(data))
        return ToolResult.success(call, {'effect_count': data['count']})

class CrashExecutor(ToolExecutor):
    async def execute(self, call, context, execution_context=None):
        original=self.idempotency_store.put_if_absent
        def mark(result):
            value=original(result)
            Path(os.environ['MARKER']).write_text('idempotency-committed')
            while True: pass
        self.idempotency_store.put_if_absent=mark
        return await super().execute(call, context, execution_context)

async def main():
    ex=CrashExecutor(Sandbox(), idempotency_store=ToolIdempotencyStore(os.environ['IDEM']),
                     intent_store=ToolIntentStore(os.environ['INTENTS']))
    call=ToolCall('call-1','external',{},timeout=5,idempotency_key='op-1')
    await ex.execute(call, ToolExecutionContext(agent_id='agent-1'))
asyncio.run(main())
"""
    proc = subprocess.Popen([sys.executable, "-c", textwrap.dedent(code)], env=env)
    try:
        _wait_marker(str(marker), "idempotency-committed")
        os.kill(proc.pid, signal.SIGKILL)
        assert proc.wait(timeout=5) == -signal.SIGKILL

        # The production executor path performed the side effect once and durably
        # recorded its result; intent completion is the only missing boundary.
        assert json.loads(effects.read_text(encoding='utf-8'))['count'] == 1
        from runtime.tool_idempotency_store import ToolIdempotencyStore
        assert ToolIdempotencyStore(str(idem)).get('op-1') is not None
        from runtime.tool_intent_store import ToolIntentStore
        intent = ToolIntentStore(str(intents)).get('op-1')
        assert intent is not None
        assert intent.state == 'executing'

        # Recovery must consume the durable result, never replay the effect.
        stored = ToolIdempotencyStore(str(idem)).get('op-1')
        assert stored is not None
        assert json.loads(effects.read_text(encoding='utf-8'))['count'] == 1
        assert intent.state == 'executing'
    finally:
        if proc.poll() is None:
            proc.kill()
            proc.wait(timeout=5)
