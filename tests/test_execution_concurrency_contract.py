import pytest

from runtime.execution_store import ExecutionConcurrencyError, ExecutionStore


def test_stale_version_cannot_overwrite_execution(tmp_path):
    store = ExecutionStore(str(tmp_path / "executions.json"))
    state = store.create("execution-1", status="pending", fencing_token=7)
    first = store.transition("execution-1", "running", expected_version=state.version, fencing_token=7)

    with pytest.raises(ExecutionConcurrencyError, match="version conflict"):
        store.transition(
            "execution-1",
            "completed",
            expected_version=state.version,
            fencing_token=7,
        )

    assert store.get("execution-1").status == "running"
    assert store.get("execution-1").version == first.version


def test_stale_fencing_token_cannot_mutate_current_execution(tmp_path):
    store = ExecutionStore(str(tmp_path / "executions.json"))
    state = store.create("execution-2", status="pending", fencing_token=11)

    with pytest.raises(ExecutionConcurrencyError, match="fencing conflict"):
        store.transition(
            "execution-2",
            "running",
            expected_version=state.version,
            fencing_token=10,
        )

    assert store.get("execution-2").status == "pending"
    assert store.get("execution-2").version == state.version


def test_current_fencing_token_allows_canonical_transition(tmp_path):
    store = ExecutionStore(str(tmp_path / "executions.json"))
    state = store.create("execution-3", status="pending", fencing_token=21)

    updated = store.transition(
        "execution-3",
        "running",
        expected_version=state.version,
        fencing_token=21,
    )

    assert updated.status == "running"
    assert updated.fencing_token == 21
    assert updated.version == state.version + 1
