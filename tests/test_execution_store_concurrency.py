from runtime.execution_audit import ExecutionAuditLog
from runtime.execution_store import ExecutionState, ExecutionStore


def test_transition_preserves_single_canonical_audit_event(tmp_path):
    audit = ExecutionAuditLog(str(tmp_path / "audit.jsonl"))
    store = ExecutionStore(str(tmp_path / "executions.json"), audit_log=audit)
    store.save(ExecutionState("e1", status="pending"))

    store.transition("e1", "running")

    events = audit.events("e1")
    assert len(events) == 1
    assert events[0].from_status == "pending"
    assert events[0].to_status == "running"


def test_repository_lock_does_not_change_snapshot_semantics(tmp_path):
    store = ExecutionStore(str(tmp_path / "executions.json"))
    store.save(ExecutionState("e1", status="pending", goal="g"))
    state = store.transition("e1", "running", goal="updated")

    assert state.status == "running"
    assert store.get("e1").goal == "updated"
