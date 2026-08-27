"""Regression coverage for deterministic recovery after journal corruption."""

from pathlib import Path

from runtime.execution_audit import ExecutionAuditLog
from runtime.execution_commit import ExecutionCommit, ExecutionCommitCoordinator
from runtime.execution_store import ExecutionStore


def _coordinator(tmp_path):
    return ExecutionCommitCoordinator(
        ExecutionStore(str(tmp_path / "executions.json")),
        ExecutionAuditLog(str(tmp_path / "audit.jsonl")),
        journal_path=str(tmp_path / "commits.jsonl"),
        quarantine_path=str(tmp_path / "quarantine.jsonl"),
    )


def test_recovery_preserves_valid_prefix_and_quarantines_corruption(tmp_path):
    coordinator = _coordinator(tmp_path)
    valid = ExecutionCommit(
        "exec-27:1:completed:corr-27",
        "exec-27",
        "running",
        "completed",
        1,
        {"ok": True},
        correlation_id="corr-27",
    )
    coordinator._append_journal(valid)
    journal = Path(coordinator.journal_path)
    journal.write_text(
        journal.read_text(encoding="utf-8") + "{broken-json}\n",
        encoding="utf-8",
    )

    first = coordinator._read_journal()
    second = coordinator._read_journal()

    assert [item.commit_id for item in first] == [valid.commit_id]
    assert [item.commit_id for item in second] == [valid.commit_id]
    quarantine = Path(coordinator.quarantine_path).read_text(encoding="utf-8")
    assert "broken-json" in quarantine


def test_recovery_does_not_promote_quarantined_data(tmp_path):
    coordinator = _coordinator(tmp_path)
    Path(coordinator.journal_path).write_text(
        '{"commit_id":"valid:1","execution_id":"exec-27","from_state":"running","to_state":"completed","sequence":1,"metadata":{}}\n'
        "{not-json}\n",
        encoding="utf-8",
    )

    commits = coordinator._read_journal()

    assert len(commits) == 1
    assert commits[0].commit_id == "valid:1"
    assert not Path(coordinator.quarantine_path).read_text(encoding="utf-8").strip() == "{not-json}"
