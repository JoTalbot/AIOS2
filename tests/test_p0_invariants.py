"""Cross-layer P0 invariants: stale execution owners must never win a race."""

import pytest

from runtime.distributed_execution_repository import DistributedExecutionRepository
from runtime.execution_store import ExecutionConcurrencyError, ExecutionState


def test_version_and_fencing_are_checked_as_one_mutation_boundary():
    repo = DistributedExecutionRepository()
    repo.create(ExecutionState("e1", fencing_token=10))

    current = repo.compare_and_set(
        "e1", expected_version=0, fencing_token=10, status="running"
    )
    assert current.version == 1

    # An old worker has the previous version and must lose even with the right fence.
    with pytest.raises(ExecutionConcurrencyError):
        repo.compare_and_set(
            "e1", expected_version=0, fencing_token=10, status="completed"
        )

    # A worker with the current version but an old lease generation must also lose.
    with pytest.raises(ExecutionConcurrencyError):
        repo.compare_and_set(
            "e1", expected_version=1, fencing_token=9, status="completed"
        )


def test_only_current_owner_can_commit_next_state():
    repo = DistributedExecutionRepository()
    repo.create(ExecutionState("e2", fencing_token=22))
    repo.compare_and_set("e2", expected_version=0, fencing_token=22, status="running")
    done = repo.compare_and_set(
        "e2", expected_version=1, fencing_token=22, status="completed"
    )
    assert (done.status, done.version, done.fencing_token) == ("completed", 2, 22)
