import pytest

from runtime.execution_store import ExecutionFencingConflictError, ExecutionState, ExecutionStore, ExecutionVersionConflictError


def test_transition_is_linearized_under_shared_store_lock(tmp_path):
    store = ExecutionStore(str(tmp_path / "executions.json"))
    state = store.save(ExecutionState("e1", status="running", attempt=1))

    updated = store.transition("e1", "completed", result={"winner": True})

    assert updated.version == state.version + 1
    assert store.get("e1").status == "completed"
    assert store.get("e1").result == {"winner": True}


def test_transition_fenced_rejects_stale_version_before_mutation(tmp_path):
    store = ExecutionStore(str(tmp_path / "executions.json"))
    state = store.save(ExecutionState("e2", status="running", attempt=1))
    winner = store.transition("e2", "completed", result="winner")

    with pytest.raises(ExecutionVersionConflictError):
        store.transition_fenced(
            "e2",
            "failed",
            state.version,
            expected_status="running",
            fencing_token=1,
            fencing_validator=lambda execution_id, token: True,
            error="stale",
        )

    current = store.get("e2")
    assert current.version == winner.version
    assert current.status == "completed"
    assert current.result == "winner"


def test_transition_fenced_validates_fencing_inside_atomic_transition(tmp_path):
    store = ExecutionStore(str(tmp_path / "executions.json"))
    state = store.save(ExecutionState("e3", status="running", attempt=1))

    with pytest.raises(ExecutionFencingConflictError):
        store.transition_fenced(
            "e3",
            "completed",
            state.version,
            expected_status="running",
            fencing_token=7,
            fencing_validator=lambda execution_id, token: False,
        )

    current = store.get("e3")
    assert current.version == state.version
    assert current.status == "running"
