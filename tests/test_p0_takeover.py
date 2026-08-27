"""P0 fencing takeover proof."""

import pytest

from runtime.distributed_execution_repository import DistributedExecutionRepository
from runtime.execution_store import ExecutionConcurrencyError, ExecutionState


def test_old_worker_is_fenced_after_owner_generation_changes():
    repo = DistributedExecutionRepository()
    repo.create(ExecutionState("e1", fencing_token=1))
    repo.compare_and_set("e1", expected_version=0, fencing_token=1, status="running")

    # Simulate an atomic lease takeover: the new owner advances the generation.
    current = repo.get("e1")
    current.fencing_token = 2
    repo._states["e1"] = current

    with pytest.raises(ExecutionConcurrencyError):
        repo.compare_and_set("e1", expected_version=1, fencing_token=1, status="completed")

    completed = repo.compare_and_set("e1", expected_version=1, fencing_token=2, status="completed")
    assert completed.status == "completed"
    assert completed.version == 2
