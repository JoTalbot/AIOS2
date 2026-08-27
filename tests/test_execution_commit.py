import dataclasses
import json
import os

import pytest

from runtime.execution_audit import ExecutionAuditLog, ExecutionAuditEvent
from runtime.execution_commit import ExecutionCommit, ExecutionCommitCoordinator
from runtime.execution_store import ExecutionState, ExecutionStore


def test_commit_persists_state_and_audit(tmp_path):
    store = ExecutionStore(str(tmp_path / "executions.json"))
    audit = ExecutionAuditLog(str(tmp_path / "audit.jsonl"))
    coordinator = ExecutionCommitCoordinator(store, audit, str(tmp_path / "commits.jsonl"))
    store.save(ExecutionState("e1", status="pending", correlation_id="corr-1"))
    coordinator.commit(store.get("e1"), "running", reason="worker-start")
    assert store.get("e1").status == "running"
    assert len(audit.events("e1")) == 1


def test_reconcile_repairs_interrupted_commit(tmp_path):
    store = ExecutionStore(str(tmp_path / "executions.json"))
    audit = ExecutionAuditLog(str(tmp_path / "audit.jsonl"))
    coordinator = ExecutionCommitCoordinator(store, audit, str(tmp_path / "commits.jsonl"))
    store.save(ExecutionState("e1", status="pending"))
    coordinator._append_journal(ExecutionCommit("c1", "e1", "pending", "running", 0, reason="crash"))
    repaired = coordinator.reconcile()
    assert repaired == ["c1"]
    assert store.get("e1").status == "running"
    assert audit.events("e1")[0].event_id == "c1"


def test_corrupt_line_does_not_poison_following_valid_sequence(tmp_path):
    store = ExecutionStore(str(tmp_path / "executions.json"))
    audit = ExecutionAuditLog(str(tmp_path / "audit.jsonl"))
    journal = tmp_path / "commits.jsonl"
    coordinator = ExecutionCommitCoordinator(store, audit, str(journal))

    first = ExecutionCommit("c1", "e1", "pending", "running", 0).with_integrity()
    second = ExecutionCommit("c2", "e1", "running", "completed", 0, sequence=2).with_integrity()
    journal.write_text(
        "{malformed}\n" + json.dumps(dataclasses.asdict(second)) + "\n",
        encoding="utf-8",
    )

    commits = coordinator.pending(all_statuses=True)
    assert [commit.commit_id for commit in commits] == ["c2"]
    appended = coordinator._append_journal(first)
    assert appended.sequence == 3
    assert len(coordinator.pending(all_statuses=True)) == 2


def test_reconcile_is_idempotent_after_audit_write(tmp_path):
    store = ExecutionStore(str(tmp_path / "executions.json"))
    audit = ExecutionAuditLog(str(tmp_path / "audit.jsonl"))
    coordinator = ExecutionCommitCoordinator(store, audit, str(tmp_path / "commits.jsonl"))
    store.save(ExecutionState("e1", status="pending"))
    coordinator._append_journal(ExecutionCommit("c1", "e1", "pending", "running", 0))

    original_mark = coordinator._mark
    coordinator._mark = lambda *args: (_ for _ in ()).throw(RuntimeError("crash-after-audit"))
    with pytest.raises(RuntimeError):
        coordinator.reconcile()
    assert store.get("e1").status == "running"
    assert [e.event_id for e in audit.events("e1")] == ["c1"]

    coordinator._mark = original_mark
    assert coordinator.reconcile() == ["c1"]
    assert [e.event_id for e in audit.events("e1")] == ["c1"]


def test_audit_append_is_idempotent_by_commit_identity(tmp_path):
    audit = ExecutionAuditLog(str(tmp_path / "audit.jsonl"))
    event = ExecutionAuditEvent("e1", "pending", "running", event_id="c1")
    assert audit.append(event).event_id == "c1"
    assert audit.append(event).event_id == "c1"
    assert len(audit.events("e1")) == 1


def test_corrupt_journal_line_is_durably_quarantined(tmp_path, monkeypatch):
    store = ExecutionStore(str(tmp_path / "executions.json"))
    audit = ExecutionAuditLog(str(tmp_path / "audit.jsonl"))
    journal = tmp_path / "commits.jsonl"
    quarantine = tmp_path / "commits.quarantine.jsonl"
    coordinator = ExecutionCommitCoordinator(store, audit, str(journal), str(quarantine))
    journal.write_text("{malformed}\n", encoding="utf-8")

    fsync_calls = []
    real_fsync = os.fsync
    monkeypatch.setattr("runtime.execution_commit.os.fsync", lambda fd: (fsync_calls.append(fd), real_fsync(fd))[1])
    assert coordinator.pending(all_statuses=True) == []
    assert quarantine.exists()
    assert quarantine.read_text(encoding="utf-8").strip()
    assert fsync_calls
