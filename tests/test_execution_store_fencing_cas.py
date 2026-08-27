import pytest

from runtime.execution_store import (
    ExecutionFencingConflictError,
    ExecutionState,
    ExecutionStore,
)


def test_compare_and_set_rejects_fencing_token_when_validator_fences_worker(tmp_path):
    store = ExecutionStore(str(tmp_path / "executions.json"))
    state = store.save(ExecutionState("e1", status="running", attempt=1))
    current = store.get("e1")
    current.status = "completed"
    with pytest.raises(ExecutionFencingConflictError):
        store.compare_and_set(
            current,
            state.version,
            expected_status="running",
            fencing_token=7,
            fencing_validator=lambda execution_id, token: False,
        )
    assert store.get("e1").status == "running"


def test_compare_and_set_requires_both_version_and_status(tmp_path):
    store = ExecutionStore(str(tmp_path / "executions.json"))
    state = store.save(ExecutionState("e2", status="running", attempt=1))
    store.transition("e2", "failed", error="winner")
    current = ExecutionState("e2", status="completed", attempt=1, version=state.version)
    with pytest.raises(RuntimeError):
        store.compare_and_set(
            current,
            state.version,
            expected_status="running",
            fencing_token=1,
            fencing_validator=lambda execution_id, token: True,
        )
    assert store.get("e2").status == "failed"


def test_fencing_token_without_validator_fails_closed(tmp_path):
    store = ExecutionStore(str(tmp_path / "executions.json"))
    state = store.save(ExecutionState("e3", status="running"))
    current = store.get("e3")
    current.status = "completed"
    with pytest.raises(ExecutionFencingConflictError):
        store.compare_and_set(current, state.version, fencing_token=11)
    assert store.get("e3").status == "running"


def test_store_level_fencing_validator_covers_plain_save_and_transition(tmp_path):
    accepted = {"token": 7}
    store = ExecutionStore(
        str(tmp_path / "executions.json"),
        fencing_validator=lambda execution_id, token: token == accepted["token"],
    )
    state = store.save(ExecutionState("e4", status="running"), fencing_token=7)

    stale = store.get("e4")
    stale.status = "failed"
    with pytest.raises(ExecutionFencingConflictError):
        store.save(stale, fencing_token=6)
    assert store.get("e4").status == "running"

    current = store.get("e4")
    current.status = "completed"
    store.save(current, fencing_token=7)
    assert store.get("e4").status == "completed"


def test_transition_carries_fence_to_atomic_cas(tmp_path):
    store = ExecutionStore(str(tmp_path / "executions.json"))
    store.save(ExecutionState("e5", status="running"))
    with pytest.raises(ExecutionFencingConflictError):
        store.transition(
            "e5",
            "completed",
            fencing_token=9,
            fencing_validator=lambda execution_id, token: False,
        )
    assert store.get("e5").status == "running"
