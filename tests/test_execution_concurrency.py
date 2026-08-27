import pytest

from runtime.execution_audit import ExecutionAuditLog
from runtime.execution_commit import ExecutionCommitCoordinator
from runtime.execution_store import ExecutionConcurrencyError, ExecutionState, ExecutionStore


def make_store(tmp_path):
    store = ExecutionStore(str(tmp_path / "executions.json"))
    state = ExecutionState("e1", status="pending")
    store.save(state)
    return store


def test_stale_worker_cannot_transition(tmp_path):
    store = make_store(tmp_path)
    first = store.get("e1")
    second = store.get("e1")
    store.transition("e1", "running", expected_version=first.version)
    with pytest.raises(ExecutionConcurrencyError):
        store.transition("e1", "running", expected_version=second.version)


def test_stale_fence_cannot_mutate(tmp_path):
    store = make_store(tmp_path)
    store.transition("e1", "running", expected_version=0, fencing_token=2)
    with pytest.raises(ExecutionConcurrencyError):
        store.transition("e1", "completed", expected_version=1, fencing_token=1)


def test_coordinator_carries_cas_and_fence(tmp_path):
    audit = ExecutionAuditLog(str(tmp_path / "audit.jsonl"))
    store = ExecutionStore(str(tmp_path / "executions.json"), audit_log=audit)
    state = ExecutionState("e1", status="pending", fencing_token=7)
    store.save(state)
    coordinator = ExecutionCommitCoordinator(store, audit, str(tmp_path / "journal.jsonl"), str(tmp_path / "quarantine.jsonl"))
    coordinator.commit(state, "running", fencing_token=7)
    current = store.get("e1")
    assert current.version == 1
    assert current.fencing_token == 7
