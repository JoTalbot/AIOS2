"""Deterministic P0 crash-window matrix.

The tests model the externally visible invariant: an interrupted commit may
be recovered, but recovery must not create a second lifecycle mutation.
"""

from runtime.execution_store import ExecutionState
from runtime.distributed_execution_repository import DistributedExecutionRepository


def test_crash_before_store_leaves_state_unchanged():
    repo = DistributedExecutionRepository()
    repo.create(ExecutionState("e1", fencing_token=9))
    before = repo.get("e1")
    assert before.version == 0
    assert before.status == "pending"


def test_retry_after_store_is_idempotent_by_version():
    repo = DistributedExecutionRepository()
    repo.create(ExecutionState("e1", fencing_token=9))
    first = repo.compare_and_set("e1", expected_version=0, fencing_token=9, status="running")
    assert first.version == 1
    assert repo.get("e1").status == "running"

    # A retried operation carrying the old version cannot duplicate the commit.
    from runtime.execution_store import ExecutionConcurrencyError
    try:
        repo.compare_and_set("e1", expected_version=0, fencing_token=9, status="running")
    except ExecutionConcurrencyError:
        pass
    else:
        raise AssertionError("stale retry must not duplicate lifecycle mutation")


def test_fenced_worker_cannot_recover_after_takeover():
    repo = DistributedExecutionRepository()
    repo.create(ExecutionState("e1", fencing_token=11))
    repo.compare_and_set("e1", expected_version=0, fencing_token=11, status="running")

    # New owner has advanced the fencing generation.
    current = repo.get("e1")
    current.fencing_token = 12
    repo._states["e1"] = current

    from runtime.execution_store import ExecutionConcurrencyError
    try:
        repo.compare_and_set("e1", expected_version=1, fencing_token=11, status="completed")
    except ExecutionConcurrencyError:
        pass
    else:
        raise AssertionError("fenced worker must be rejected")
