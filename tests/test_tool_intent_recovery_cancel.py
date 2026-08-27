import asyncio
import json
from datetime import datetime, timedelta, timezone

import pytest

from runtime.tool_intent_store import ToolIntent, ToolIntentStore
from runtime.tool_intent_recovery import ToolIntentRecoveryWorker


class PendingExecutor:
    async def reconcile_intent(self, intent, resolver):
        await asyncio.sleep(10)


def _expire_claim(store, key="k"):
    raw = json.loads(store.path.read_text(encoding="utf-8"))
    raw[key]["claim_expires_at"] = (datetime.now(timezone.utc) - timedelta(seconds=1)).isoformat()
    store.path.write_text(json.dumps(raw), encoding="utf-8")


def test_cancelled_recovery_does_not_terminalize(tmp_path):
    async def run():
        store = ToolIntentStore(str(tmp_path / "intents.json"), claim_ttl_seconds=5)
        store.prepare(ToolIntent("k", "c", "write", {}))
        worker = ToolIntentRecoveryWorker(store, max_attempts=1)
        task = asyncio.create_task(worker.recover(PendingExecutor(), lambda _: None))
        await asyncio.sleep(0)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        intent = store.get("k")
        assert intent.state == "executing"
        assert intent.owner_id is not None
        assert intent.claim_token is not None
    asyncio.run(run())


def test_cancelled_recovery_can_be_reclaimed_after_expiry(tmp_path):
    async def run():
        store = ToolIntentStore(str(tmp_path / "intents.json"), claim_ttl_seconds=60)
        store.prepare(ToolIntent("k", "c", "write", {}))
        worker = ToolIntentRecoveryWorker(store, max_attempts=1)
        task = asyncio.create_task(worker.recover(PendingExecutor(), lambda _: None))
        await asyncio.sleep(0)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        _expire_claim(store)
        reclaimed = store.claim("k", "fresh-owner", "fresh-token")
        assert reclaimed is not None
        assert store.mark_claimed("k", "fresh-owner", "fresh-token", "completed") is not None
        assert store.get("k").state == "completed"
    asyncio.run(run())
