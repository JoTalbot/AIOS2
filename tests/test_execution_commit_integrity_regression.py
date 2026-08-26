import pytest

from runtime.execution_audit import ExecutionAuditLog
from runtime.execution_commit import ExecutionCommitCoordinator
from runtime.execution_store import ExecutionState, ExecutionStore
from runtime.recovery_manager import RecoveryManager


def test_applied_commit_keeps_valid_checksum(tmp_path):
    store = ExecutionStore(str(tmp_path / "executions.json"))
    audit = ExecutionAuditLog(str(tmp_path / "audit.jsonl"))
    coordinator = ExecutionCommitCoordinator(store, audit, str(tmp_path / "commits.jsonl"))
    store.save(ExecutionState("e1", status="pending"))

    commit = coordinator.commit(store.get("e1"), "running")

    assert coordinator.pending() == []
    journal = coordinator._read_journal()
    assert len(journal) == 1
    assert journal[0].commit_id == commit.commit_id
    assert journal[0].status == "applied"
    assert journal[0].with_integrity().checksum == journal[0].checksum


def test_repeated_commit_is_idempotent_after_applied_status(tmp_path):
    store = ExecutionStore(str(tmp_path / "executions.json"))
    audit = ExecutionAuditLog(str(tmp_path / "audit.jsonl"))
    coordinator = ExecutionCommitCoordinator(store, audit, str(tmp_path / "commits.jsonl"))
    store.save(ExecutionState("e1", status="pending"))
    state = store.get("e1")

    first = coordinator.commit(state, "running")
    second = coordinator.commit(store.get("e1"), "running")

    assert second.commit_id == first.commit_id
    assert len(coordinator._read_journal()) == 1
    assert len(audit.events("e1")) == 1


def test_recovery_manager_rejects_noncanonical_failure_mutation(tmp_path):
    store = ExecutionStore(str(tmp_path / "executions.json"))
    state = ExecutionState("e1", status="running")
    store.save(state)

    with pytest.raises(RuntimeError, match="canonical commit coordinator"):
        RecoveryManager(store).mark_failed(state, RuntimeError("boom"))
