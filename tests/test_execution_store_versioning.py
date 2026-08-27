import pytest

from runtime.execution_store import ExecutionState, ExecutionStore, ExecutionVersionConflictError


def test_save_assigns_monotonic_versions(tmp_path):
    store = ExecutionStore(str(tmp_path / "executions.json"))
    state = store.save(ExecutionState("e1"))
    assert state.version == 1
    state.status = "running"
    state = store.save(state)
    assert state.version == 2


def test_compare_and_set_rejects_stale_writer(tmp_path):
    store = ExecutionStore(str(tmp_path / "executions.json"))
    state = store.save(ExecutionState("e1"))
    stale = store.get("e1")
    current = store.get("e1")

    current.status = "running"
    store.compare_and_set(current, expected_version=state.version)

    stale.status = "running"
    with pytest.raises(ExecutionVersionConflictError):
        store.compare_and_set(stale, expected_version=state.version)

    assert store.get("e1").version == 2
    assert store.get("e1").status == "running"
