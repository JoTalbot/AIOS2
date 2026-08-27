"""P0 event durability invariant tests."""

from runtime.execution_audit import ExecutionAuditLog
from runtime.execution_commit import ExecutionCommitCoordinator
from runtime.execution_store import ExecutionState, ExecutionStore


def test_commit_audit_is_derived_from_committed_transition(tmp_path):
    audit = ExecutionAuditLog(str(tmp_path / "audit.jsonl"))
    store = ExecutionStore(str(tmp_path / "execution.json"), audit_log=audit)
    state = ExecutionState("e1", status="pending", fencing_token=3)
    store.save(state)
    coordinator = ExecutionCommitCoordinator(store, audit, str(tmp_path / "journal.jsonl"), str(tmp_path / "quarantine.jsonl"))

    coordinator.commit(state, "running", fencing_token=3)

    persisted = store.get("e1")
    records = audit.read_all()
    assert persisted.status == "running"
    assert persisted.version == 1
    assert records
    assert records[-1]["execution_id"] == "e1"
    assert records[-1]["to_status"] == "running"
    assert records[-1]["version"] == 1


def test_failed_precommit_does_not_emit_committed_event(tmp_path):
    audit = ExecutionAuditLog(str(tmp_path / "audit.jsonl"))
    store = ExecutionStore(str(tmp_path / "execution.json"), audit_log=audit)
    state = ExecutionState("e1", status="pending", fencing_token=3)
    store.save(state)
    assert audit.read_all() == []
    assert store.get("e1").version == 0
