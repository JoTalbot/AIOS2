import json

import pytest

from runtime.execution_store import ExecutionState, ExecutionStore, ExecutionStoreCorruptionError


def test_corrupted_execution_store_is_detected(tmp_path):
    path = tmp_path / "executions.json"
    path.write_text("{broken-json", encoding="utf-8")

    store = ExecutionStore(str(path))

    with pytest.raises(ExecutionStoreCorruptionError):
        store.get("missing")


def test_atomic_rewrite_keeps_previous_state(tmp_path):
    path = tmp_path / "executions.json"
    store = ExecutionStore(str(path))
    store.save(ExecutionState("exec-safe", goal="before"))

    raw = json.loads(path.read_text(encoding="utf-8"))
    assert raw["exec-safe"]["goal"] == "before"

    restored = ExecutionStore(str(path))
    assert restored.get("exec-safe").goal == "before"


def test_version_conflict_blocks_stale_writer(tmp_path):
    from runtime.execution_store import ExecutionVersionConflictError

    store = ExecutionStore(str(tmp_path / "executions.json"))
    state = ExecutionState("exec-race")
    store.save(state)

    with pytest.raises(ExecutionVersionConflictError):
        store.compare_and_set(ExecutionState("exec-race", goal="stale"), 0)
