"""Multiprocess side-effect/idempotency race and crash-recovery invariants."""
import json
import multiprocessing as mp
import os
import signal
import subprocess
import sys
import time

from runtime.tool_idempotency_store import StoredToolResult, ToolIdempotencyStore


def _winner(path, key, barrier, queue):
    store = ToolIdempotencyStore(path)
    barrier.wait()
    result = store.put_if_absent(
        StoredToolResult(key, "call-1", "external", True, {"winner": os.getpid()})
    )
    queue.put((os.getpid(), result is not None))


def test_concurrent_recovery_has_exactly_one_idempotency_winner(tmp_path):
    path = str(tmp_path / "idempotency.json")
    ctx = mp.get_context("spawn")
    barrier = ctx.Barrier(12)
    queue = ctx.Queue()
    workers = [ctx.Process(target=_winner, args=(path, "op-1", barrier, queue)) for _ in range(12)]
    for p in workers:
        p.start()
    results = [queue.get(timeout=15) for _ in workers]
    for p in workers:
        p.join(timeout=10)
        assert p.exitcode == 0
    assert sum(won for _, won in results) == 1
    stored = ToolIdempotencyStore(path).get("op-1")
    assert stored is not None


def test_sigkill_after_side_effect_then_competing_recovery_is_at_most_once(tmp_path):
    marker = tmp_path / "marker"
    effects = tmp_path / "effects.json"
    idem = tmp_path / "idempotency.json"
    env = os.environ.copy()
    env["PYTHONPATH"] = os.getcwd()
    env.update(MARKER=str(marker), EFFECTS=str(effects), IDEM=str(idem))
    code = """
import json, os
from pathlib import Path
p=Path(os.environ['EFFECTS'])
p.write_text(json.dumps({'count': 1, 'key': 'op-1'}))
Path(os.environ['MARKER']).write_text('effect')
while True: pass
"""
    dead = subprocess.Popen([sys.executable, "-c", code], env=env)
    try:
        deadline = time.time() + 5
        while time.time() < deadline and not marker.exists():
            time.sleep(0.01)
        assert marker.exists()
        os.kill(dead.pid, signal.SIGKILL)
        assert dead.wait(timeout=5) == -signal.SIGKILL

        ctx = mp.get_context("spawn")
        barrier = ctx.Barrier(8)
        queue = ctx.Queue()
        workers = [ctx.Process(target=_winner, args=(str(idem), "op-1", barrier, queue)) for _ in range(8)]
        for p in workers: p.start()
        results = [queue.get(timeout=15) for _ in workers]
        for p in workers:
            p.join(timeout=10)
            assert p.exitcode == 0
        assert sum(won for _, won in results) == 1
        assert json.loads(effects.read_text(encoding='utf-8'))['count'] == 1
        assert ToolIdempotencyStore(str(idem)).get('op-1') is not None
    finally:
        if dead.poll() is None:
            dead.kill()
            dead.wait(timeout=5)


def test_idempotency_winner_is_stable_across_recovery_retries(tmp_path):
    path = str(tmp_path / "idempotency.json")
    store = ToolIdempotencyStore(path)
    first = StoredToolResult("op-2", "call-1", "external", True, {"attempt": 1})
    assert store.put_if_absent(first) is not None
    for attempt in range(2, 20):
        candidate = StoredToolResult("op-2", f"call-{attempt}", "external", True, {"attempt": attempt})
        assert store.put_if_absent(candidate) is None
    assert store.get("op-2").value == {"attempt": 1}
