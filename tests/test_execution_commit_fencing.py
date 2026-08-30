from runtime.execution_audit import ExecutionAuditLog
from runtime.execution_commit import ExecutionCommit, ExecutionCommitCoordinator
from runtime.execution_lease import ExecutionLeaseStore
from runtime.execution_store import ExecutionState, ExecutionStore


def test_stale_fencing_token_cannot_reconcile_pending_commit(tmp_path):
    leases = ExecutionLeaseStore(str(tmp_path / "leases.json")); store = ExecutionStore(str(tmp_path / "executions.json")); audit = ExecutionAuditLog(str(tmp_path / "audit.jsonl"))
    store.save(ExecutionState("e1", status="running", attempt=1, correlation_id="c1")); old = leases.acquire("e1", "node-a")
    coordinator = ExecutionCommitCoordinator(store, audit, str(tmp_path / "commits.jsonl"), lease_store=leases, lease_owner_id="node-a", fencing_token=old.fencing_token)
    coordinator._append_journal(ExecutionCommit("c1", "e1", "running", "completed", 1, {"stale": True}, correlation_id="c1"))
    assert leases.release("e1", "node-a", old.fencing_token); new = leases.acquire("e1", "node-b"); assert new.fencing_token > old.fencing_token
    assert coordinator.reconcile() == []; assert store.get("e1").status == "running"; assert audit.events("e1") == []; assert len(coordinator.pending()) == 1


def test_commit_records_intent_but_does_not_apply_after_fencing_loss(tmp_path, monkeypatch):
    leases = ExecutionLeaseStore(str(tmp_path / "leases.json")); store = ExecutionStore(str(tmp_path / "executions.json")); audit = ExecutionAuditLog(str(tmp_path / "audit.jsonl"))
    state = store.save(ExecutionState("e2", status="running", attempt=1, correlation_id="c2")); lease = leases.acquire("e2", "node-a")
    coordinator = ExecutionCommitCoordinator(store, audit, str(tmp_path / "commits.jsonl"), lease_store=leases, lease_owner_id="node-a", fencing_token=lease.fencing_token)
    original = leases.is_owner_unlocked; calls = {"count": 0}
    def fenced(*args, **kwargs):
        calls["count"] += 1
        return False if calls["count"] == 2 else original(*args, **kwargs)
    monkeypatch.setattr(leases, "is_owner_unlocked", fenced)
    commit = coordinator.commit(state, "completed", checkpoint={"ok": True})
    assert commit.status == "pending"; assert store.get("e2").status == "running"; assert audit.events("e2") == []; assert coordinator.pending()[0].commit_id == commit.commit_id
