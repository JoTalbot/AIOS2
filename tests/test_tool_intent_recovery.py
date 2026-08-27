import asyncio

import pytest

from runtime.execution_lease import ExecutionLeaseStore
from runtime.tool_executor import ToolExecutor
from runtime.tool_intent_recovery import ToolIntentRecoveryWorker
from runtime.tool_intent_store import ToolIntent, ToolIntentStore
from runtime.tool_protocol import ToolResult


class Resolver:
    def __init__(self, result=None, delay=0.0):
        self.calls = 0
        self.result = result
        self.delay = delay

    async def __call__(self, intent):
        self.calls += 1
        if self.delay:
            await asyncio.sleep(self.delay)
        return self.result


@pytest.mark.asyncio
async def test_recovery_is_bounded_and_does_not_replay_side_effect(tmp_path):
    store = ToolIntentStore(str(tmp_path / "intents.json"))
    intent = ToolIntent("e1:step1", "c1", "charge", {"amount": 10}, "e1", "ambiguous")
    store.prepare(intent)
    resolver = Resolver()
    worker = ToolIntentRecoveryWorker(store, max_attempts=3)
    executor = ToolExecutor(object(), intent_store=store)

    result = await worker.recover(executor, resolver)

    assert result[0].status == "quarantined"
    assert result[0].attempts == 3
    assert resolver.calls == 3
    assert store.get(intent.idempotency_key).state == "ambiguous"


@pytest.mark.asyncio
async def test_stale_recovery_worker_is_fenced(tmp_path):
    store = ToolIntentStore(str(tmp_path / "intents.json"))
    leases = ExecutionLeaseStore(str(tmp_path / "leases.json"))
    intent = ToolIntent("e2:step1", "c2", "charge", {}, "e2", "ambiguous")
    store.prepare(intent)
    first = leases.acquire(intent.idempotency_key, "node-a")
    assert first is not None
    leases.release(intent.idempotency_key, "node-a", first.fencing_token)
    second = leases.acquire(intent.idempotency_key, "node-b")
    assert second is not None

    worker = ToolIntentRecoveryWorker(store, leases, "node-a")
    executor = ToolExecutor(object(), intent_store=store)
    result = await worker.recover(executor, Resolver())

    assert result[0].status == "skipped_by_lease"


@pytest.mark.asyncio
async def test_concurrent_recovery_allows_only_one_claim_owner(tmp_path):
    store = ToolIntentStore(str(tmp_path / "intents.json"))
    intent = ToolIntent("e3:step1", "c3", "charge", {}, "e3", "ambiguous")
    store.prepare(intent)
    result = ToolResult.success(type("Call", (), {"call_id": "c3", "tool": "charge", "idempotency_key": "e3:step1"})(), {"recovered": True})
    worker_a = ToolIntentRecoveryWorker(store, owner_id="node-a")
    worker_b = ToolIntentRecoveryWorker(store, owner_id="node-b")
    executor = ToolExecutor(object(), intent_store=store)
    resolver = Resolver(result=result, delay=0.02)

    outcomes = await asyncio.gather(
        worker_a.recover(executor, resolver),
        worker_b.recover(executor, resolver),
    )

    statuses = {outcomes[0][0].status, outcomes[1][0].status}
    assert statuses == {"recovered", "skipped_by_claim"}
    assert resolver.calls == 1
    assert store.get(intent.idempotency_key).state == "completed"


@pytest.mark.asyncio
async def test_concurrent_recovery_with_lease_allows_one_fencing_owner(tmp_path):
    store = ToolIntentStore(str(tmp_path / "intents.json"))
    leases = ExecutionLeaseStore(str(tmp_path / "leases.json"))
    intent = ToolIntent("e4:step1", "c4", "charge", {}, "e4", "ambiguous")
    store.prepare(intent)
    result = ToolResult.success(type("Call", (), {"call_id": "c4", "tool": "charge", "idempotency_key": "e4:step1"})(), {"recovered": True})
    worker_a = ToolIntentRecoveryWorker(store, leases, "node-a")
    worker_b = ToolIntentRecoveryWorker(store, leases, "node-b")
    executor = ToolExecutor(object(), intent_store=store)
    resolver = Resolver(result=result, delay=0.02)

    outcomes = await asyncio.gather(
        worker_a.recover(executor, resolver),
        worker_b.recover(executor, resolver),
    )

    statuses = {outcomes[0][0].status, outcomes[1][0].status}
    assert statuses == {"recovered", "skipped_by_lease"}
    assert resolver.calls == 1
    assert store.get(intent.idempotency_key).state == "completed"


def test_recovery_claim_token_contains_lease_fencing_epoch(tmp_path):
    import asyncio
    from runtime.execution_lease import ExecutionLeaseStore
    from runtime.tool_intent_store import ToolIntent, ToolIntentStore
    from runtime.intent_recovery_worker import IntentRecoveryWorker

    async def run():
        path = str(tmp_path / "intents.json")
        lease_path = str(tmp_path / "leases.json")
        store = ToolIntentStore(path)
        leases = ExecutionLeaseStore(lease_path)
        store.prepare(ToolIntent("k", "c", "write", {}, "exec"))
        worker = IntentRecoveryWorker(store, leases, "worker-a")
        captured = {}
        def resolver(item):
            captured["token"] = item.claim_token
            return "completed", {"ok": True}
        result = worker.recover_one(store.get("k"), resolver)
        assert result.status == "completed"
        assert captured["token"].startswith("recovery:worker-a:1:")
    asyncio.run(run())
