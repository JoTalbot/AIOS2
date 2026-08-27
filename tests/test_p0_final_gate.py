"""Final P0 integration gate for the canonical execution primitives."""

import pytest

from runtime.distributed_execution_repository import DistributedExecutionRepository
from runtime.execution_store import ExecutionConcurrencyError, ExecutionState
from runtime.sqlite_execution_repository import SQLiteExecutionRepository


@pytest.mark.parametrize("factory", [DistributedExecutionRepository])
def test_canonical_lifecycle_preserves_version_and_fence(factory):
    repo = factory()
    repo.create(ExecutionState("e1", status="pending", fencing_token=21))
    running = repo.compare_and_set("e1", expected_version=0, fencing_token=21, status="running")
    completed = repo.compare_and_set("e1", expected_version=1, fencing_token=21, status="completed")
    assert (running.version, completed.version) == (1, 2)
    assert completed.fencing_token == 21


def test_sqlite_final_gate_rejects_stale_worker(tmp_path):
    repo = SQLiteExecutionRepository(str(tmp_path / "final.db"))
    repo.create(ExecutionState("e1", status="pending", fencing_token=21))
    repo.compare_and_set("e1", expected_version=0, fencing_token=21, status="running")
    current = repo.get("e1")
    current.fencing_token = 22
    # Simulates a new lease owner committing its generation.
    with repo._connect() as db:
        import json
        db.execute("UPDATE executions SET state_json=?, fencing_token=? WHERE execution_id=?", (json.dumps(current.__dict__), 22, "e1"))
    with pytest.raises(ExecutionConcurrencyError):
        repo.compare_and_set("e1", expected_version=1, fencing_token=21, status="completed")
