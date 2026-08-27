import pytest

from runtime.execution_store import ExecutionConcurrencyError, ExecutionState, ExecutionStore


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
    assert loaded.version == 0
    assert len(restored.resumable()) == 1


def test_execution_store_updates_status_and_increments_version(tmp_path):
    store = ExecutionStore(str(tmp_path / "executions.json"))
    store.save(ExecutionState("exec-2"))
    initial = store.get("exec-2")
    updated = store.transition("exec-2", "completed", expected_version=initial.version)
    assert updated.status == "completed"
    assert updated.version == initial.version + 1
    assert store.resumable() == []


def test_execution_store_rejects_stale_version(tmp_path):
    store = ExecutionStore(str(tmp_path / "executions.json"))
    store.save(ExecutionState("exec-3"))
    initial = store.get("exec-3")
    store.transition("exec-3", "running", expected_version=initial.version)
    with pytest.raises(ExecutionConcurrencyError):
        store.transition("exec-3", "failed", expected_version=initial.version)


def test_execution_store_rejects_stale_fencing_generation(tmp_path):
    store = ExecutionStore(str(tmp_path / "executions.json"))
    store.save(ExecutionState("exec-4", fencing_token=2))
    current = store.get("exec-4")
    with pytest.raises(ExecutionConcurrencyError):
        store.transition("exec-4", "running", expected_version=current.version, fencing_token=1)
