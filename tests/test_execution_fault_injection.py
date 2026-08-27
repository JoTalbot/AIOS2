import json

import pytest

from runtime.execution_audit import ExecutionAuditLog
from runtime.execution_commit import ExecutionCommitCoordinator
from runtime.execution_lease import ExecutionLeaseStore
from runtime.execution_store import ExecutionState, ExecutionStore, ExecutionVersionConflictError


def _coordinator(tmp_path, *, fenced=False):
    lock = tmp_path / "execution.lock"
    leases = ExecutionLeaseStore(str(tmp_path / "leases.json"), coordination_lock_path=str(lock))
    store = ExecutionStore(str(tmp_path / "executions.json"), coordination_lock_path=str(lock))
    audit = ExecutionAuditLog(str(tmp_path / "audit.jsonl"))
    store.save(ExecutionState("e1", status="running", attempt=1, correlation_id="c1"))
    lease = leases.acquire("e1", "node-a")
    coordinator = ExecutionCommitCoordinator(
        store, audit, str(tmp_path / "commits.jsonl"),
        lease_store=leases, lease_owner_id="node-a", fencing_token=lease.fencing_token,
    )
    if fenced:
        assert leases.release("e1", "node-a", lease.fencing_token)
        assert leases.acquire("e1", "node-b").fencing_token > lease.fencing_token
    return store, audit, leases, lease, coordinator


def test_crash_before_journal_is_a_noop(tmp_path):
    store, audit, leases, lease, coordinator = _coordinator(tmp_path)
    original = coordinator._append_journal
    coordinator._append_journal = lambda commit: (_ for _ in ()).throw(OSError("crash before journal"))
    with pytest.raises(OSError):
        coordinator.commit(store.get("e1"), "completed", checkpoint={"ok": True})
    assert store.get("e1").status == "running"
    assert audit.events("e1") == []
    assert coordinator.pending() == []
    assert not (tmp_path / "commits.jsonl").read_text(encoding="utf-8")


def test_journal_before_cas_recovers(tmp_path, monkeypatch):
    store, audit, leases, lease, coordinator = _coordinator(tmp_path)
    original = store.compare_and_set
    calls = {"n": 0}

    def crash_before_cas(*args, **kwargs):
        calls["n"] += 1
        raise OSError("crash before CAS")

    monkeypatch.setattr(store, "compare_and_set", crash_before_cas)
    with pytest.raises(OSError):
        coordinator.commit(store.get("e1"), "completed", checkpoint={"ok": True})
    assert store.get("e1").status == "running"
    assert len(coordinator.pending()) == 1

    monkeypatch.setattr(store, "compare_and_set", original)
    assert coordinator.reconcile() == [coordinator.pending()[0].commit_id]
    assert store.get("e1").status == "completed"
    assert len(audit.events("e1")) == 1
    assert coordinator.pending() == []


def test_cas_before_mark_reconciles_without_duplicate_state_transition(tmp_path, monkeypatch):
    store, audit, leases, lease, coordinator = _coordinator(tmp_path)
    original_mark = coordinator._mark

    def crash_before_mark(*args, **kwargs):
        raise OSError("crash after CAS before mark")

    monkeypatch.setattr(coordinator, "_mark", crash_before_mark)
    with pytest.raises(OSError):
        coordinator.commit(store.get("e1"), "completed", checkpoint={"ok": True})
    assert store.get("e1").status == "completed"
    assert len(coordinator.pending()) == 1
    assert len(audit.events("e1")) == 1

    monkeypatch.setattr(coordinator, "_mark", original_mark)
    assert coordinator.reconcile() == [coordinator.pending()[0].commit_id]
    assert store.get("e1").status == "completed"
    assert len(audit.events("e1")) == 2
    assert coordinator.pending() == []


def test_lease_loss_before_cas_never_applies_stale_write(tmp_path, monkeypatch):
    store, audit, leases, lease, coordinator = _coordinator(tmp_path)
    original = coordinator._lease_valid_unlocked
    calls = {"n": 0}

    def lose_lease(execution_id):
        calls["n"] += 1
        if calls["n"] == 2:
            assert leases.release("e1", "node-a", lease.fencing_token)
            assert leases.acquire("e1", "node-b").fencing_token > lease.fencing_token
        return original(execution_id)

    monkeypatch.setattr(coordinator, "_lease_valid_unlocked", lose_lease)
    commit = coordinator.commit(store.get("e1"), "completed", checkpoint={"stale": True})
    assert commit.status == "pending"
    assert store.get("e1").status == "running"
    assert audit.events("e1") == []
    assert len(coordinator.pending()) == 1


def test_lease_loss_before_reconcile_cas_leaves_intent_pending(tmp_path, monkeypatch):
    store, audit, leases, lease, coordinator = _coordinator(tmp_path)
    commit = coordinator._append_journal(
        coordinator.commit(store.get("e1"), "completed", checkpoint={"ok": True})
    ) if False else None
    # Construct a durable journal entry without applying it.
    from runtime.execution_commit import ExecutionCommit
    journal_commit = coordinator._append_journal(
        ExecutionCommit("manual:e1:1:completed:1", "e1", "running", "completed", 1, {"ok": True}, correlation_id="c1", expected_version=1, fencing_token=lease.fencing_token)
    )
    original = coordinator._lease_valid_unlocked
    calls = {"n": 0}

    def lose_before_cas(execution_id):
        calls["n"] += 1
        if calls["n"] == 2:
            assert leases.release("e1", "node-a", lease.fencing_token)
            assert leases.acquire("e1", "node-b").fencing_token > lease.fencing_token
        return original(execution_id)

    monkeypatch.setattr(coordinator, "_lease_valid_unlocked", lose_before_cas)
    assert coordinator.reconcile() == []
    assert store.get("e1").status == "running"
    assert coordinator.pending()[0].commit_id == journal_commit.commit_id
    assert audit.events("e1") == []


def test_fault_matrix_preserves_durable_json_after_failed_transition(tmp_path):
    store, _, _, _, _ = _coordinator(tmp_path)
    before = json.loads((tmp_path / "executions.json").read_text(encoding="utf-8"))
    stale = store.get("e1")
    newer = store.get("e1")
    newer.status = "completed"
    store.compare_and_set(newer, newer.version)
    stale.status = "failed"
    with pytest.raises(ExecutionVersionConflictError):
        store.compare_and_set(stale, stale.version)
    after = json.loads((tmp_path / "executions.json").read_text(encoding="utf-8"))
    assert after["e1"]["status"] == "completed"
    assert after["e1"]["version"] == before["e1"]["version"] + 1
