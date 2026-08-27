"""End-to-end multiprocess chaos around ToolExecutor idempotency recovery."""
import asyncio
import json
import multiprocessing as mp
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


def _crashing_executor(env):
    code = r'''
import asyncio, json, os
from pathlib import Path
from runtime.tool_executor import ToolExecutor
from runtime.tool_idempotency_store import ToolIdempotencyStore
from runtime.tool_protocol import ToolCall, ToolResult
from runtime.tool_sandbox import ToolExecutionContext

class Sandbox:
    async def execute(self, call, context, execution_context=None):
        p=Path(os.environ['EFFECTS'])
        data=json.loads(p.read_text()) if p.exists() else {'count':0}
        data['count'] += 1
        p.write_text(json.dumps(data))
        Path(os.environ['MARKER']).write_text('side-effect')
        while True: await asyncio.sleep(1)

async def main():
    executor=ToolExecutor(Sandbox(), idempotency_store=ToolIdempotencyStore(os.environ['IDEM']))
    call=ToolCall('call-1','external',{},idempotency_key='op-1')
    await executor.execute(call, ToolExecutionContext(agent_id='a1'))
asyncio.run(main())
'''
    return subprocess.Popen([sys.executable, "-c", textwrap.dedent(code)], env=env)


def _recover(env):
    code = r'''
import json, os
from pathlib import Path
from runtime.tool_idempotency_store import ToolIdempotencyStore, StoredToolResult
store=ToolIdempotencyStore(os.environ['IDEM'])
# Reconciliation records the observed side effect exactly once; it never calls Sandbox.
if store.get('op-1') is None:
    store.put_if_absent(StoredToolResult('op-1','call-1','external',True,{'reconciled':True}))
assert store.get('op-1') is not None
Path(os.environ['MARKER']).write_text('recovered')
'''
    return subprocess.run([sys.executable, "-c", textwrap.dedent(code)], env=env, timeout=10)


def _race_worker(path, barrier, queue):
    from runtime.tool_idempotency_store import StoredToolResult, ToolIdempotencyStore
    barrier.wait()
    result=ToolIdempotencyStore(path).put_if_absent(
        StoredToolResult('op-1','call-1','external',True,{'winner':os.getpid()}))
    queue.put(result is not None)


def test_executor_sigkill_then_16_process_recovery_has_single_side_effect_and_winner(tmp_path):
    env=os.environ.copy()
    env['PYTHONPATH']=os.getcwd()
    env['EFFECTS']=str(tmp_path/'effects.json')
    env['IDEM']=str(tmp_path/'idempotency.json')
    env['MARKER']=str(tmp_path/'marker')
    dead=_crashing_executor(env)
    try:
        _wait_marker(env['MARKER'],'side-effect')
        os.kill(dead.pid, signal.SIGKILL)
        assert dead.wait(timeout=5) == -signal.SIGKILL

        ctx=mp.get_context('spawn')
        barrier=ctx.Barrier(16)
        queue=ctx.Queue()
        workers=[ctx.Process(target=_race_worker,args=(env['IDEM'],barrier,queue)) for _ in range(16)]
        for p in workers: p.start()
        wins=[queue.get(timeout=20) for _ in workers]
        for p in workers:
            p.join(timeout=10)
            assert p.exitcode == 0
        assert sum(wins) == 1
        assert json.loads(open(env['EFFECTS']).read())['count'] == 1
        assert _recover(env).returncode == 0
        assert open(env['MARKER']).read() == 'recovered'
    finally:
        if dead.poll() is None:
            dead.kill(); dead.wait(timeout=5)
