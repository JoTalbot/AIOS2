import json
import threading

from runtime.execution_audit import ExecutionAuditLog
from runtime.execution_commit import ExecutionCommit, ExecutionCommitCoordinator
from runtime.execution_store import ExecutionStore


def test_concurrent_journal_appends_have_unique_contiguous_sequences(tmp_path):
    store = ExecutionStore(str(tmp_path / "executions.json"))
    audit = ExecutionAuditLog(str(tmp_path / "audit.jsonl"))
    journal = tmp_path / "commits.jsonl"
    coordinator = ExecutionCommitCoordinator(store, audit, str(journal))

    workers = 12
    barrier = threading.Barrier(workers)
    commits = []
    errors = []
    lock = threading.Lock()

    def worker(index):
        try:
            barrier.wait(timeout=5)
            commit = coordinator._append_journal(
                ExecutionCommit(f"c{index}", "e1", "pending", "running", index)
            )
            with lock:
                commits.append(commit)
        except Exception as exc:
            with lock:
                errors.append(exc)

    threads = [threading.Thread(target=worker, args=(i,), daemon=True) for i in range(workers)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=10)

    assert not errors
    assert all(not thread.is_alive() for thread in threads)
    assert len(commits) == workers

    entries = coordinator.pending(all_statuses=True)
    sequences = sorted(commit.sequence for commit in entries)
    assert sequences == list(range(1, workers + 1))
    assert len({commit.commit_id for commit in entries}) == workers

    for commit in entries:
        payload = json.loads(
            next(
                line
                for line in journal.read_text(encoding="utf-8").splitlines()
                if json.loads(line)["commit_id"] == commit.commit_id
            )
        )
        assert commit.with_integrity().checksum == payload["checksum"]
