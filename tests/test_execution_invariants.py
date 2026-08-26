import json

from runtime.execution_audit import ExecutionAuditLog
from runtime.execution_commit import ExecutionCommit, ExecutionCommitCoordinator
from runtime.execution_lease import ExecutionLeaseStore
from runtime.execution_store import ExecutionState, ExecutionStore


def build_runtime(tmp_path):
    audit = ExecutionAuditLog(str(tmp_path / "audit.jsonl"))
    store = ExecutionStore(str(tmp_path / "executions.json"), audit_log=audit)
    coordinator = ExecutionCommitCoordinator(store, audit, str(tmp_path / "commits.jsonl"), str(tmp_path / "quarantine.jsonl"))
    return store, audit, coordinator


def test_canonical_commit_emits_one_audit_event(tmp_path):
    store, audit, coordinator = build_runtime(tmp_path)
    store.save(ExecutionState("e1", status="pending", correlation_id="c1"))

    coordinator.commit(store.get("e1"), "running", reason="start")

    assert store.get("e1").status == "running"
    assert len(audit.events("e1")) == 1
    assert audit.events("e1")[0].to_status == "running"


def test_reconcile_is_idempotent(tmp_path):
    store, audit, coordinator = build_runtime(tmp_path)
    store.save(ExecutionState("e1", status="pending"))
    coordinator._append_journal(ExecutionCommit("c1", "e1", "pending", "running", 0, reason="crash"))

    assert coordinator.reconcile() == ["c1"]
    assert coordinator.reconcile() == []
    assert len(audit.events("e1")) == 1


def test_journal_survives_quarantined_record(tmp_path):
    store, audit, coordinator = build_runtime(tmp_path)
    store.save(ExecutionState("e1", status="pending"))
    coordinator.commit(store.get("e1"), "running")
    with (tmp_path / "commits.jsonl").open("a", encoding="utf-8") as handle:
        handle.write("not-json\n")

    commit = coordinator._append_journal(ExecutionCommit("c2", "e1", "running", "retrying", 0))
    assert commit.sequence == 3
    commits = coordinator._read_journal()
    assert [item.sequence for item in commits] == [1, 3]


def test_lease_denies_live_owner_to_second_worker(tmp_path):
    path = str(tmp_path / "leases.json")
    first = ExecutionLeaseStore(path, ttl_seconds=60)
    second = ExecutionLeaseStore(path, ttl_seconds=60)

    assert first.acquire("e1", "worker-a") is not None
    assert second.acquire("e1", "worker-b") is None
    assert first.is_owner("e1", "worker-a")
    assert not second.is_owner("e1", "worker-b")
