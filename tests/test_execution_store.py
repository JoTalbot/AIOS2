import pytest

from runtime.execution_store import ExecutionState, ExecutionStore, ExecutionVersionConflictError


def test_execution_store_persists_and_recovers(tmp_path):
    store = ExecutionStore(str(tmp_path / "executions.json"))
    state = ExecutionState("exec-1", goal="demo", attempt=1, plan=[{"tool": "x"}])
    store.save(state)
    restored = ExecutionStore(str(tmp_path / "executions.json"))
    loaded = restored.get("exec-1")
    assert loaded is not None
    assert loaded.goal == "demo"
    assert loaded.attempt == 1
    assert loaded.plan == [{"tool": "x"}]
    assert len(restored.resumable()) == 1


def test_execution_store_updates_status_with_observed_version(tmp_path):
    store = ExecutionStore(str(tmp_path / "executions.json"))
    state = store.save(ExecutionState("exec-2"))
    state.status = "completed"
    state.result = "ok"
    store.save(state)
    assert store.get("exec-2").status == "completed"
    assert store.resumable() == []


def test_save_rejects_stale_writer_instead_of_last_write_wins(tmp_path):
    store = ExecutionStore(str(tmp_path / "executions.json"))
    state = store.save(ExecutionState("exec-3"))
    stale = store.get("exec-3")
    winner = store.get("exec-3")

    winner.status = "running"
    store.save(winner)

    stale.status = "failed"
    with pytest.raises(ExecutionVersionConflictError):
        store.save(stale)

    assert store.get("exec-3").status == "running"


def test_new_state_with_zero_version_cannot_overwrite_existing_execution(tmp_path):
    store = ExecutionStore(str(tmp_path / "executions.json"))
    store.save(ExecutionState("exec-4", status="running"))

    with pytest.raises(ExecutionVersionConflictError):
        store.save(ExecutionState("exec-4", status="completed"))

    assert store.get("exec-4").status == "running"
