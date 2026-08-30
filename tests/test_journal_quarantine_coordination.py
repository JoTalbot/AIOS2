"""Regression coverage for journal corruption quarantine coordination."""

from pathlib import Path

from runtime.execution_commit import ExecutionCommit, ExecutionCommitCoordinator
from runtime.execution_store import ExecutionStore
from runtime.execution_audit import ExecutionAuditLog


def _coordinator(tmp_path):
    return ExecutionCommitCoordinator(
        ExecutionStore(str(tmp_path / "executions.json")),
        ExecutionAuditLog(str(tmp_path / "audit.jsonl")),
        journal_path=str(tmp_path / "commits.jsonl"),
        quarantine_path=str(tmp_path / "quarantine.jsonl"),
    )


def test_corrupt_journal_line_is_quarantined_without_losing_valid_commits(tmp_path):
    coordinator = _coordinator(tmp_path)
    coordinator._append_journal(
        ExecutionCommit(
            "exec-26:1:completed:corr-26",
            "exec-26",
            "running",
            "completed",
            1,
            {"ok": True},
            correlation_id="corr-26",
        )
    )
    journal = Path(coordinator.journal_path)
    journal.write_text(
        journal.read_text(encoding="utf-8") + "{not-json}\n",
        encoding="utf-8",
    )

    commits = coordinator._read_journal()

    assert [commit.commit_id for commit in commits] == ["exec-26:1:completed:corr-26"]
    quarantine = Path(coordinator.quarantine_path).read_text(encoding="utf-8")
    assert "not-json" in quarantine
    assert "reason" in quarantine


def test_quarantine_write_is_serialized_by_journal_lock(tmp_path, monkeypatch):
    coordinator = _coordinator(tmp_path)
    calls = []

    class ObservedLock:
        def __enter__(self):
            calls.append("enter")
            return self

        def __exit__(self, *args):
            calls.append("exit")
            return False

    monkeypatch.setattr(
        "runtime.execution_commit._JournalLock",
        lambda path: ObservedLock(),
    )

    Path(coordinator.journal_path).write_text("{broken}\n", encoding="utf-8")
    coordinator._read_journal()

    assert calls == ["enter", "exit"]
