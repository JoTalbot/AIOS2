import pytest

from runtime.recovery_checkpoint import RecoveryCheckpoint
from runtime.execution_lease import ExecutionLeaseStore
from runtime.execution_store import ExecutionState, ExecutionStore
from runtime.lease_aware_checkpoint import LeaseAwareCheckpoint


def test_checkpoint_requires_current_fencing_token(tmp_path):
    leases = ExecutionLeaseStore(str(tmp_path / "leases.json"))
    store = ExecutionStore(str(tmp_path / "executions.json"))
    state = store.save(ExecutionState("e1"))
    checkpoint = LeaseAwareCheckpoint(RecoveryCheckpoint(store), leases, "node-a")

    lease = leases.acquire("e1", "node-a")
    assert lease is not None

    with pytest.raises(ValueError, match="fencing_token"):
        checkpoint.mark_running(state, 1)

    checkpoint.mark_running(state, 1, fencing_token=lease.fencing_token)
    assert store.get("e1").status == "running"


def test_stale_owner_cannot_checkpoint(tmp_path):
    leases = ExecutionLeaseStore(str(tmp_path / "leases.json"))
    store = ExecutionStore(str(tmp_path / "executions.json"))
    state = store.save(ExecutionState("e1"))
    checkpoint = LeaseAwareCheckpoint(RecoveryCheckpoint(store), leases, "node-a")

    lease = leases.acquire("e1", "node-a")
    assert lease is not None
    leases.release("e1", "node-a", lease.fencing_token)
    newer = leases.acquire("e1", "node-b")
    assert newer is not None

    with pytest.raises(RuntimeError, match="not owned"):
        checkpoint.mark_running(state, 1, fencing_token=lease.fencing_token)
