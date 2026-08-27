from runtime.execution_audit import ExecutionAuditLog, ExecutionAuditEvent
from runtime.execution_commit import ExecutionCommitCoordinator, ExecutionCommit
from runtime.execution_store import ExecutionState, ExecutionStore


def test_audit_append_is_idempotent_for_same_event_identity(tmp_path):
    audit = ExecutionAuditLog(str(tmp_path / "audit.jsonl"))
    event = ExecutionAuditEvent("e1", "pending", "running", 1, event_id="c1")

    first = audit.append(event)
    second = audit.append(event)

    assert first == second
    assert audit.events("e1") == [first]


def test_reconcile_emits_one_audit_event_for_already_applied_commit(tmp_path):
    store = ExecutionStore(str(tmp_path / "executions.json"))
    audit = ExecutionAuditLog(str(tmp_path / "audit.jsonl"))
    coordinator = ExecutionCommitCoordinator(store, audit, str(tmp_path / "commits.jsonl"))
    store.save(ExecutionState("e1", status="pending"))
    coordinator._append_journal(ExecutionCommit("c1", "e1", "pending", "running", 0))

    assert coordinator.reconcile() == ["c1"]
    assert coordinator.reconcile() == []
    assert len(audit.events("e1")) == 1
    assert audit.events("e1")[0].event_id == "c1"


def test_commit_retry_with_same_commit_id_does_not_duplicate_audit(tmp_path):
    store = ExecutionStore(str(tmp_path / "executions.json"))
    audit = ExecutionAuditLog(str(tmp_path / "audit.jsonl"))
    coordinator = ExecutionCommitCoordinator(store, audit, str(tmp_path / "commits.jsonl"))
    state = ExecutionState("e1", status="pending", attempt=1, correlation_id="r1")
    store.save(state)

    first = coordinator.commit(state, "running")
    second = coordinator.commit(state, "running")

    assert first.commit_id == second.commit_id
    assert len(audit.events("e1")) == 1
