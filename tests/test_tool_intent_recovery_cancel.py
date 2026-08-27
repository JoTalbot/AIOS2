import asyncio
import pytest
from runtime.tool_intent_store import ToolIntent, ToolIntentStore
from runtime.tool_intent_recovery import ToolIntentRecoveryWorker

class PendingExecutor:
    async def reconcile_intent(self, intent, resolver):
        await asyncio.sleep(10)

def test_cancelled_recovery_does_not_terminalize(tmp_path):
    async def run():
        store = ToolIntentStore(str(tmp_path / "intents.json"), claim_ttl_seconds=5)
        store.prepare(ToolIntent("k", "c", "write", {}))
        worker = ToolIntentRecoveryWorker(store, max_attempts=1)
        task = asyncio.create_task(worker.recover(PendingExecutor(), lambda _: None))
        await asyncio.sleep(0)
        task.cancel()
        with pytest.raises(asyncio.CancelledError): await task
        intent = store.get("k")
        assert intent.state == "executing"
    asyncio.run(run())
