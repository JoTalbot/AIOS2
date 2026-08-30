import pytest

from runtime.execution_store import ExecutionFencingConflictError, ExecutionState, ExecutionStore


def test_compare_and_set_rejects_fencing_token_when_validator_fences_worker(tmp_path):
    store = ExecutionStore(str(tmp_path / "executions.json"))
    state = store.save(ExecutionState("e1", status="running", attempt=1))
    with pytest.raises(ExecutionFencingConflictError):
        store.compare_and_set(ExecutionState("e1", status="completed", attempt=1), state.version, expected_status="running", fencing_token=7, fencing_validator=lambda execution_id, token: False)
    assert store.get("e1").status == "running"


def test_compare_and_set_requires_both_version_and_status(tmp_path):
    store = ExecutionStore(str(tmp_path / "executions.json"))
    state = store.save(ExecutionState("e2", status="running", attempt=1))
    store.transition("e2", "failed", error="winner")
    with pytest.raises(RuntimeError):
        store.compare_and_set(ExecutionState("e2", status="completed", attempt=1), state.version, expected_status="running", fencing_token=1, fencing_validator=lambda execution_id, token: True)
    assert store.get("e2").status == "failed"
