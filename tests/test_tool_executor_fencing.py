import asyncio

from runtime.tool_executor import ToolExecutor
from runtime.tool_intent_store import ToolIntent, ToolIntentStore
from runtime.tool_protocol import ToolResult
from runtime.tool_sandbox import ToolSandbox


def test_reconcile_standalone_terminalizes_unclaimed_intent(tmp_path):
    store = ToolIntentStore(str(tmp_path / "intents.json"), claim_ttl_seconds=10)
    store.prepare(ToolIntent("k", "c", "write", {}))
    store.mark("k", "ambiguous")
    worker = ToolExecutor(ToolSandbox(), intent_store=store)

    async def run():
        result = await worker.reconcile_intent(
            store.get("k"),
            lambda _: ToolResult("c", "write", True, "ok", None, False, "k"),
        )
        assert result.ok

    asyncio.run(run())
    assert store.get("k").state == "completed"


def test_reconcile_does_not_bypass_active_claim(tmp_path):
    store = ToolIntentStore(str(tmp_path / "intents.json"), claim_ttl_seconds=10)
    store.prepare(ToolIntent("k", "c", "write", {}))
    claimed = store.claim("k", "owner", "token")
    assert claimed is not None
    worker = ToolExecutor(ToolSandbox(), intent_store=store)

    async def run():
        result = await worker.reconcile_intent(
            store.get("k"),
            lambda _: ToolResult("c", "write", True, "ok", None, False, "k"),
        )
        assert result.ok

    asyncio.run(run())
    current = store.get("k")
    assert current.state == "executing"
    assert current.owner_id == "owner"
    assert current.claim_token == "token"
