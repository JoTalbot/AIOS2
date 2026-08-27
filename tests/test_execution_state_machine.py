import pytest

from runtime.execution_store import ExecutionState, ExecutionStore
from runtime.execution_state_machine import ExecutionStateMachine, InvalidExecutionTransition


def test_valid_execution_lifecycle(tmp_path):
    store = ExecutionStore(str(tmp_path / "executions.json"))
    state = store.save(ExecutionState("e1", status="pending"))
    assert state.status == "pending"
    store.transition("e1", "running")
    store.transition("e1", "retrying")
    store.transition("e1", "running", attempt=1)
    store.transition("e1", "completed", result="done")
    assert store.get("e1").status == "completed"


def test_invalid_transition_is_rejected(tmp_path):
    store = ExecutionStore(str(tmp_path / "executions.json"))
    store.save(ExecutionState("e1", status="pending"))
    with pytest.raises(InvalidExecutionTransition):
        store.transition("e1", "completed")


def test_completed_execution_cannot_restart(tmp_path):
    store = ExecutionStore(str(tmp_path / "executions.json"))
    store.save(ExecutionState("e1", status="pending"))
    store.transition("e1", "running")
    store.transition("e1", "completed")
    with pytest.raises(InvalidExecutionTransition):
        store.transition("e1", "running")


def test_unknown_states_are_rejected():
    machine = ExecutionStateMachine()
    with pytest.raises(InvalidExecutionTransition, match="unknown execution state"):
        machine.validate("pending", "paused")
    with pytest.raises(InvalidExecutionTransition, match="unknown execution state"):
        machine.validate("paused", "running")


def test_custom_graph_rejects_unknown_targets():
    with pytest.raises(ValueError, match="unknown states"):
        ExecutionStateMachine({"pending": frozenset({"missing"})})
