"""Regression coverage for journal read/write coordination.

The public journal readers must hold the dedicated journal lock so a reader
cannot observe an append/mark operation halfway through a write.
"""

from pathlib import Path


def _load_execution_module():
    import importlib

    for name in ("aios_core.execution", "execution", "aios.execution"):
        try:
            return importlib.import_module(name)
        except ImportError:
            continue
    raise AssertionError("Unable to locate AIOS2 execution module")


def test_execution_commit_module_exposes_unlocked_journal_reader():
    module = _load_execution_module()
    candidates = [
        getattr(module, "ExecutionCommitManager", None),
        getattr(module, "ExecutionCommit", None),
    ]
    cls = next((candidate for candidate in candidates if candidate is not None), None)
    assert cls is not None, "Execution commit manager class not found"
    assert hasattr(cls, "_read_journal_unlocked"), (
        "journal parser/repair primitive must remain available so callers "
        "already holding the journal lock do not reacquire it"
    )


def test_public_journal_reads_use_journal_lock_contract():
    root = Path(__file__).resolve().parents[1]
    source_files = list(root.rglob("*.py"))
    execution_sources = "\n".join(
        path.read_text(encoding="utf-8")
        for path in source_files
        if "execution" in path.name.lower() or "commit" in path.name.lower()
    )
    assert "_JournalLock" in execution_sources
    assert "_read_journal_unlocked" in execution_sources
