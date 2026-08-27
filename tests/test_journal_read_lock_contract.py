"""Regression coverage for journal read/write coordination."""

from pathlib import Path


def test_execution_commit_module_exposes_unlocked_journal_reader():
    from runtime.execution_commit import ExecutionCommitCoordinator

    assert hasattr(ExecutionCommitCoordinator, "_read_journal_unlocked")


def test_public_journal_reads_use_journal_lock_contract():
    root = Path(__file__).resolve().parents[1]
    source = root / "runtime" / "execution_commit.py"
    execution_source = source.read_text(encoding="utf-8")

    assert "class _JournalLock" in execution_source
    assert "def _read_journal_unlocked" in execution_source
    assert "def _read_journal(self)" in execution_source
    assert "with _JournalLock(self.lock_path)" in execution_source
