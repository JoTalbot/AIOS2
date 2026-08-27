import pytest

from runtime.execution_store import ExecutionState, ExecutionStore


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


def test_execution_store_updates_status(tmp_path):
    store = ExecutionStore(str(tmp_path / "executions.json"))
    store.save(ExecutionState("exec-2"))
    store.save(ExecutionState("exec-2", status="completed", result="ok"))
    assert store.get("exec-2").status == "completed"
    assert store.resumable() == []


def test_fencing_token_requires_validator(tmp_path):
    from runtime.execution_store import ExecutionFencingConflictError, ExecutionState, ExecutionStore
    store = ExecutionStore(str(tmp_path / "executions.json"))
    with pytest.raises(ExecutionFencingConflictError):
        store.compare_and_set(ExecutionState("exec-fence"), 0, fencing_token=1)


def test_fencing_validator_can_reject_write(tmp_path):
    from runtime.execution_store import ExecutionFencingConflictError, ExecutionState, ExecutionStore
    store = ExecutionStore(str(tmp_path / "executions.json"))
    with pytest.raises(ExecutionFencingConflictError):
        store.compare_and_set(ExecutionState("exec-fence"), 0, fencing_token=1, fencing_validator=lambda *_: False)
    assert store.get("exec-fence") is None

# CI trigger: fencing regression suite must execute on the current workflow attempt.
