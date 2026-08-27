import multiprocessing

import pytest

from runtime.execution_store import ExecutionConcurrencyError, ExecutionState
from runtime.sqlite_execution_repository import SQLiteExecutionRepository


def test_sqlite_cas_and_fencing(tmp_path):
    repo = SQLiteExecutionRepository(str(tmp_path / "execution.db"))
    repo.create(ExecutionState("e1", fencing_token=5))
    state = repo.compare_and_set("e1", expected_version=0, fencing_token=5, status="running")
    assert state.version == 1
    with pytest.raises(ExecutionConcurrencyError):
        repo.compare_and_set("e1", expected_version=0, fencing_token=5, status="completed")
    with pytest.raises(ExecutionConcurrencyError):
        repo.compare_and_set("e1", expected_version=1, fencing_token=4, status="completed")


def _race(path, queue):
    repo = SQLiteExecutionRepository(path)
    try:
        state = repo.compare_and_set("e1", expected_version=0, fencing_token=5, status="running")
        queue.put(("accepted", state.version))
    except ExecutionConcurrencyError:
        queue.put(("rejected", None))


def test_two_processes_have_one_cas_winner(tmp_path):
    path = str(tmp_path / "race.db")
    repo = SQLiteExecutionRepository(path)
    repo.create(ExecutionState("e1", fencing_token=5))
    queue = multiprocessing.Queue()
    workers = [multiprocessing.Process(target=_race, args=(path, queue)) for _ in range(2)]
    for worker in workers:
        worker.start()
    for worker in workers:
        worker.join()
    results = [queue.get() for _ in workers]
    assert sum(result[0] == "accepted" for result in results) == 1
    assert repo.get("e1").version == 1
