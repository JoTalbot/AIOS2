"""Multiprocess idempotency contention: exactly one durable winner."""
import multiprocessing as mp
import os
import time

from runtime.tool_idempotency_store import StoredToolResult, ToolIdempotencyStore


def _writer(path, barrier, queue, owner):
    store = ToolIdempotencyStore(path)
    barrier.wait(timeout=10)
    result = store.put_if_absent(
        StoredToolResult("same-key", owner, "external", True, {"owner": owner})
    )
    queue.put((owner, result))


def test_concurrent_recovery_workers_have_single_idempotency_winner(tmp_path):
    path = str(tmp_path / "idempotency.json")
    ctx = mp.get_context("spawn")
    barrier = ctx.Barrier(12)
    queue = ctx.Queue()
    workers = [ctx.Process(target=_writer, args=(path, barrier, queue, f"w{i}")) for i in range(12)]
    for p in workers:
        p.start()
    results = [queue.get(timeout=15) for _ in workers]
    for p in workers:
        p.join(timeout=15)
        assert p.exitcode == 0

    winners = [owner for owner, result in results if result is not None]
    assert len(winners) == 1
    stored = ToolIdempotencyStore(path).get("same-key")
    assert stored is not None
    assert stored.call_id == winners[0]


def test_recovery_retry_after_crash_is_idempotent(tmp_path):
    path = str(tmp_path / "idempotency.json")
    store = ToolIdempotencyStore(path)
    first = store.put_if_absent(
        StoredToolResult("same-key", "recovery-1", "external", True, {"ok": True})
    )
    assert first is not None

    ctx = mp.get_context("spawn")
    queue = ctx.Queue()
    barrier = ctx.Barrier(6)
    workers = [ctx.Process(target=_writer, args=(path, barrier, queue, f"retry-{i}")) for i in range(6)]
    for p in workers:
        p.start()
    results = [queue.get(timeout=15) for _ in workers]
    for p in workers:
        p.join(timeout=15)
        assert p.exitcode == 0
    assert all(result is None for _, result in results)
    assert ToolIdempotencyStore(path).get("same-key").call_id == "recovery-1"
