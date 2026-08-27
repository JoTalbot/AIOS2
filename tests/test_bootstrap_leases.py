import asyncio

import pytest

from runtime.execution_lease import ExecutionLeaseStore
from runtime.execution_store import ExecutionState, ExecutionStore
from runtime.runtime_bootstrap import RuntimeBootstrap


@pytest.mark.asyncio
async def test_bootstrap_skips_execution_owned_by_another_runtime(tmp_path):
    store = ExecutionStore(str(tmp_path / "executions.json"))
    leases = ExecutionLeaseStore(str(tmp_path / "leases.json"), ttl_seconds=60)
    store.save(ExecutionState("e1", status="running"))
    assert leases.acquire("e1", "other-runtime") is not None

    resumed = []

    async def resume(state):
        resumed.append(state.execution_id)

    report = await RuntimeBootstrap(
        store, lease_store=leases, owner_id="this-runtime"
    ).recover_pending(resume)
    assert report.skipped == 1
    assert report.recovered == 0
    assert resumed == []


@pytest.mark.asyncio
async def test_bootstrap_releases_lease_after_recovery(tmp_path):
    store = ExecutionStore(str(tmp_path / "executions.json"))
    leases = ExecutionLeaseStore(str(tmp_path / "leases.json"), ttl_seconds=60)
    store.save(ExecutionState("e1", status="running"))

    async def resume(state):
        return None

    report = await RuntimeBootstrap(
        store, lease_store=leases, owner_id="runtime-a"
    ).recover_pending(resume)
    assert report.recovered == 1
    assert leases.acquire("e1", "runtime-b") is not None


@pytest.mark.asyncio
async def test_bootstrap_fails_closed_when_heartbeat_loses_lease():
    class FailingHeartbeatLease:
        ttl_seconds = 30

        def acquire(self, execution_id, owner):
            return type("Lease", (), {"fencing_token": 7})()

        def renew(self, execution_id, owner, fencing_token):
            return None

        def is_owner(self, execution_id, owner, fencing_token):
            return True

        def release(self, execution_id, owner, fencing_token):
            pass

    class Store:
        def resumable(self):
            return [ExecutionState("e1", status="running")]

    cancelled = []

    async def resume(state):
        try:
            await asyncio.sleep(1)
        finally:
            cancelled.append(True)

    report = await RuntimeBootstrap(
        store=Store(),
        lease_store=FailingHeartbeatLease(),
        owner_id="runtime-a",
        heartbeat_interval=0,
    ).recover_pending(resume)

    assert report.recovered == 0
    assert report.failed == 1
    assert cancelled == [True]
