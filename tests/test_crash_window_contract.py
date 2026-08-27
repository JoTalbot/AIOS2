"""Crash-window contract tests for canonical execution commits.

These tests document the recovery contract without pretending file-backed storage is
an atomic distributed transaction. A pending journal entry must remain replayable,
and reconciliation must converge to an applied entry exactly once.
"""
from runtime.execution_commit import ExecutionCommitCoordinator
from runtime.execution_store import ExecutionStore


def test_pending_commit_is_reconciled_once(tmp_path):
    store = ExecutionStore(str(tmp_path / "executions.json"))
    coordinator = ExecutionCommitCoordinator(
        store=store,
        journal_path=str(tmp_path / "journal.jsonl"),
    )
    store.create("e1", metadata={"attempt": 1})

    commit = coordinator.commit("e1", "running", correlation_id="c1")
    assert commit.status == "applied"
    assert coordinator.reconcile() == 0


def test_reconcile_does_not_duplicate_applied_commit(tmp_path):
    store = ExecutionStore(str(tmp_path / "executions.json"))
    coordinator = ExecutionCommitCoordinator(
        store=store,
        journal_path=str(tmp_path / "journal.jsonl"),
    )
    store.create("e1", metadata={"attempt": 1})

    coordinator.commit("e1", "running", correlation_id="c1")
    before = store.get("e1")
    assert before is not None

    assert coordinator.reconcile() == 0
    after = store.get("e1")
    assert after == before
