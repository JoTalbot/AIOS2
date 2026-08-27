import pytest

from runtime.distributed_execution_repository import DistributedExecutionRepository
from runtime.execution_store import ExecutionConcurrencyError, ExecutionState


def test_distributed_repository_cas_and_fencing(tmp_path):
    repo = DistributedExecutionRepository()
    repo.create(ExecutionState("e1", fencing_token=4))
    updated = repo.compare_and_set("e1", expected_version=0, fencing_token=4, status="running")
    assert updated.version == 1
    assert updated.status == "running"

    with pytest.raises(ExecutionConcurrencyError):
        repo.compare_and_set("e1", expected_version=0, fencing_token=4, status="completed")

    with pytest.raises(ExecutionConcurrencyError):
        repo.compare_and_set("e1", expected_version=1, fencing_token=3, status="completed")
