import pytest

from runtime.execution_lease import ExecutionLeaseStore
from runtime.tool_executor import ToolExecutor
from runtime.tool_intent_recovery import ToolIntentRecoveryWorker
from runtime.tool_intent_store import ToolIntent, ToolIntentStore


class Resolver:
    def __init__(self):
        self.calls = 0

    async def __call__(self, intent):
        self.calls += 1
        return None


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
