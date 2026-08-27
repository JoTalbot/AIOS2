from runtime.execution_commit import ExecutionCommitCoordinator
from runtime.execution_store import ExecutionStore


def test_repeated_transition_is_idempotent(tmp_path):
    store = ExecutionStore(str(tmp_path / "executions.json"))
    coordinator = ExecutionCommitCoordinator(
        store=store,
        journal_path=str(tmp_path / "journal.jsonl"),
    )
    store.create("e1", metadata={"attempt": 1})

    first = coordinator.commit("e1", "running", correlation_id="same")
    second = coordinator.commit("e1", "running", correlation_id="same")

    assert second.commit_id == first.commit_id
    assert second.status == "applied"
    assert coordinator.reconcile() == 0
