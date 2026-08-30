import pytest

from runtime.execution_store import (
    ExecutionState,
    ExecutionStore,
    ExecutionVersionConflictError,
)


def test_transition_uses_observed_version_and_rejects_stale_writer(tmp_path):
    store = ExecutionStore(str(tmp_path / "executions.json"))
    store.save(ExecutionState("exec-1", status="pending", goal="demo"))

    stale = store.get("exec-1")
    current = store.get("exec-1")

    current.status = "running"
    store.compare_and_set(current, current.version)

    stale.status = "running"
    with pytest.raises(ExecutionVersionConflictError):
        store.compare_and_set(stale, stale.version)


def test_transition_updates_state_without_lost_version(tmp_path):
    store = ExecutionStore(str(tmp_path / "executions.json"))
    created = store.transition("exec-2", "pending", goal="demo")
    assert created.version == 1

    transitioned = store.transition("exec-2", "running", attempt=1)
    assert transitioned.status == "running"
    assert transitioned.attempt == 1
    assert transitioned.version == 2

    loaded = store.get("exec-2")
    assert loaded.version == 2
    assert loaded.status == "running"
