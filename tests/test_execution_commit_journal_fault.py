import pytest

from runtime.execution_audit import ExecutionAuditLog
from runtime.execution_commit import ExecutionCommitCoordinator
from runtime.execution_lease import ExecutionLeaseStore
from runtime.execution_store import ExecutionState, ExecutionStore


def _coordinator(tmp_path, store, audit, leases, lease):
    return ExecutionCommitCoordinator(
        store, audit, str(tmp_path / "commits.jsonl"),
        lease_store=leases, lease_owner_id=lease.owner_id,
        fencing_token=lease.fencing_token,
    )


def test_journal_replace_crash_preserves_old_pending_record_and_recovers(tmp_path, monkeypatch):
    leases = ExecutionLeaseStore(str(tmp_path / "leases.json"))
    store = ExecutionStore(str(tmp_path / "executions.json"))
    audit = ExecutionAuditLog(str(tmp_path / "audit.jsonl"))
    state = store.save(ExecutionState("e1", status="running", attempt=1, correlation_id="c1"))
    lease = leases.acquire("e1", "node-a")
    coordinator = _coordinator(tmp_path, store, audit, leases, lease)

    original_replace = type(coordinator.journal_path.with_suffix(coordinator.journal_path.suffix + ".tmp")).replace
    def crash_replace(self, target):
        if self.name.endswith(".tmp"):
            raise OSError("simulated crash before journal replace")
        return original_replace(self, target)
    monkeypatch.setattr(type(coordinator.journal_path), "replace", crash_replace)

    with pytest.raises(OSError, match="before journal replace"):
        coordinator.commit(state, "completed", checkpoint={"ok": True})

    assert store.get("e1").status == "completed"
    assert len(audit.events("e1")) == 1
    assert len(coordinator.pending()) == 1
    assert coordinator.pending()[0].status == "pending"

    # A fresh coordinator sees the durable old journal record and repairs it.
    recovered = _coordinator(tmp_path, store, audit, leases, lease)
    assert recovered.reconcile() == ["e1:1:completed:c1"]
    assert recovered.pending() == []
    assert len(audit.events("e1")) == 1
    assert store.get("e1").version == 2

    # A second recovery pass is a no-op.
    assert recovered.reconcile() == []
    assert len(audit.events("e1")) == 1
