import pytest

from runtime.execution_store import ExecutionFencingConflictError, ExecutionState, ExecutionStore
from runtime.recovery_manager import RecoveryManager


class _Lease:
    fencing_token = 7


class _LeaseStore:
    def __init__(self):
        self.checks = 0
        self.released = False

    def acquire(self, execution_id, owner_id):
        return _Lease()

    def is_owner(self, execution_id, owner_id, token):
        self.checks += 1
        # First check succeeds, second check fails as if another worker fenced us.
        return self.checks == 1

    def release(self, execution_id, owner_id, token):
        self.released = True


class _Loop:
    async def resume(self, execution_id, agent, context=None):
        return "done"


@pytest.mark.asyncio
async def test_recovery_rejects_lease_fenced_after_resume(tmp_path):
    store = ExecutionStore(str(tmp_path / "executions.json"))
    store.save(ExecutionState("e1", status="running", goal="resume"))
    leases = _LeaseStore()
    manager = RecoveryManager(store, leases, "worker-a")

    outcomes = await manager.recover(_Loop(), object())

    assert outcomes[0].status == "failed"
    assert store.get("e1").status == "running"
    assert leases.released is True


@pytest.mark.asyncio
async def test_recovery_does_not_mark_failed_after_fencing_race(tmp_path):
    store = ExecutionStore(str(tmp_path / "executions.json"))
    state = ExecutionState("e1", status="running", goal="resume")
    store.save(state)
    leases = _LeaseStore()
    manager = RecoveryManager(store, leases, "worker-a")

    # Force the failure path to verify mark_failed cannot cross the fencing boundary.
    def fail_resume(*args, **kwargs):
        raise RuntimeError("worker failure")

    class Loop:
        resume = fail_resume

    outcomes = await manager.recover(Loop(), object())
    assert outcomes[0].status == "failed"
    assert store.get("e1").status == "failed"
