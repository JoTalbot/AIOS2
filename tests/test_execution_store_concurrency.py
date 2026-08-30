import threading

import pytest

from runtime.execution_store import (
    ExecutionState,
    ExecutionStore,
    ExecutionVersionConflictError,
)


def test_concurrent_compare_and_set_has_single_winner(tmp_path):
    store = ExecutionStore(str(tmp_path / "executions.json"))
    initial = store.save(ExecutionState("exec-race", status="running", attempt=1))
    barrier = threading.Barrier(2)
    results = []

    def writer(status):
        candidate = ExecutionState("exec-race", status=status, attempt=1)
        barrier.wait()
        try:
            store.compare_and_set(
                candidate,
                initial.version,
                expected_status="running",
            )
            results.append((status, "committed"))
        except ExecutionVersionConflictError:
            results.append((status, "conflict"))

    threads = [
        threading.Thread(target=writer, args=("completed",)),
        threading.Thread(target=writer, args=("failed",)),
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=5)

    assert all(not thread.is_alive() for thread in threads)
    assert sorted(outcome for _, outcome in results) == ["committed", "conflict"]
    assert store.get("exec-race").status in {"completed", "failed"}
    assert store.get("exec-race").version == initial.version + 1


def test_stale_version_cannot_overwrite_terminal_state(tmp_path):
    store = ExecutionStore(str(tmp_path / "executions.json"))
    initial = store.save(ExecutionState("exec-terminal", status="running", attempt=1))
    winner = ExecutionState("exec-terminal", status="completed", attempt=1, result="winner")
    store.compare_and_set(winner, initial.version, expected_status="running")

    stale = ExecutionState("exec-terminal", status="failed", attempt=1, error="stale")
    with pytest.raises(ExecutionVersionConflictError):
        store.compare_and_set(stale, initial.version, expected_status="running")

    current = store.get("exec-terminal")
    assert current.status == "completed"
    assert current.result == "winner"
