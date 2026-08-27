import pytest

from runtime.execution_lease import ExecutionLeaseStore
from runtime.execution_store import ExecutionState, ExecutionStore
from runtime.recovery_manager import RecoveryManager


class Loop:
    async def resume(self, execution_id, agent, context=None):
        return "ok"


@pytest.mark.asyncio
async def test_recovery_uses_fencing_token_for_release(tmp_path):
    lease_store = ExecutionLeaseStore(str(tmp_path / "leases.json"))
    store = ExecutionStore(str(tmp_path / "executions.json"))
    state = ExecutionState("e1", status="running")
    store.save(state)

    manager = RecoveryManager(store, lease_store, "node-a")
    result = await manager.recover(Loop(), object())

    assert result[0].status == "recovered"
    assert lease_store.acquire("e1", "node-b") is not None


@pytest.mark.asyncio
async def test_recovery_skips_when_lease_is_lost_before_resume(tmp_path, monkeypatch):
    lease_store = ExecutionLeaseStore(str(tmp_path / "leases.json"))
    store = ExecutionStore(str(tmp_path / "executions.json"))
    store.save(ExecutionState("e1", status="running"))

    manager = RecoveryManager(store, lease_store, "node-a")
    original = lease_store.is_owner

    def lost(*args, **kwargs):
        return False

    monkeypatch.setattr(lease_store, "is_owner", lost)
    result = await manager.recover(Loop(), object())

    assert result[0].status == "skipped_by_lease"
    monkeypatch.setattr(lease_store, "is_owner", original)
