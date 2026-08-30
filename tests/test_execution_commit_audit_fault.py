import pytest

from runtime.execution_audit import ExecutionAuditLog
from runtime.execution_commit import ExecutionCommitCoordinator
from runtime.execution_lease import ExecutionLeaseStore
from runtime.execution_store import ExecutionState, ExecutionStore


def test_crash_after_audit_append_before_journal_applied_is_idempotent(tmp_path, monkeypatch):
    leases = ExecutionLeaseStore(str(tmp_path / "leases.json"))
    store = ExecutionStore(str(tmp_path / "executions.json"))
    audit = ExecutionAuditLog(str(tmp_path / "audit.jsonl"))
    state = store.save(ExecutionState("e1", status="running", attempt=1, correlation_id="c1"))
    lease = leases.acquire("e1", "node-a")
    journal = str(tmp_path / "commits.jsonl")
    coordinator = ExecutionCommitCoordinator(store, audit, journal, lease_store=leases, lease_owner_id="node-a", fencing_token=lease.fencing_token)

    original_mark = coordinator._mark
    calls = {"count": 0}
    def crash_once(*args, **kwargs):
        calls["count"] += 1
        if calls["count"] == 1:
            raise RuntimeError("simulated crash after audit append")
        return original_mark(*args, **kwargs)
    monkeypatch.setattr(coordinator, "_mark", crash_once)

    with pytest.raises(RuntimeError, match="after audit"):
        coordinator.commit(state, "completed", checkpoint={"ok": True})

    assert store.get("e1").status == "completed"
    assert len(audit.events("e1")) == 1
    assert len(coordinator.pending()) == 1

    assert coordinator.reconcile() == ["e1:1:completed:c1"]
    assert len(audit.events("e1")) == 1
    assert coordinator.pending() == []

    # A further restart/recovery pass remains idempotent.
    assert coordinator.reconcile() == []
    events = audit.events("e1")
    assert len(events) == 1
    assert events[0].event_id == "e1:1:completed:c1"


def test_audit_identity_deduplicates_recovery_append(tmp_path):
    audit = ExecutionAuditLog(str(tmp_path / "audit.jsonl"))
    from runtime.execution_audit import ExecutionAuditEvent

    event = ExecutionAuditEvent("e2", "running", "completed", 1, correlation_id="c2", event_id="stable-id")
    assert audit.append(event).event_id == "stable-id"
    assert audit.append(event).event_id == "stable-id"
    assert len(audit.events("e2")) == 1
