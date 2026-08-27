import pytest

from runtime.tool_executor import ToolExecutor
from runtime.tool_idempotency_store import ToolIdempotencyStore
from runtime.tool_intent_store import ToolIntent, ToolIntentStore
from runtime.tool_protocol import ToolResult


class ExplodingSandbox:
    async def execute(self, tool_name, context, **kwargs):
        raise OSError("connection lost after remote commit")


@pytest.mark.asyncio
async def test_failed_side_effect_becomes_ambiguous(tmp_path):
    intents = ToolIntentStore(str(tmp_path / "intents.json"))
    executor = ToolExecutor(ExplodingSandbox(), intent_store=intents)
    from runtime.tool_protocol import ToolCall
    call = ToolCall("remote_write", {"value": 1}, "c1", idempotency_key="e1:s1")
    result = await executor.execute(call, type("C", (), {"agent_id": "a"})())
    assert not result.ok
    assert intents.get("e1:s1").state == "ambiguous"


@pytest.mark.asyncio
async def test_reconciliation_resolves_without_replay(tmp_path):
    intents = ToolIntentStore(str(tmp_path / "intents.json"))
    idem = ToolIdempotencyStore(str(tmp_path / "results.json"))
    intent = intents.prepare(ToolIntent("k", "c", "remote_write", {"value": 1}, "e"))
    intents.mark("k", "ambiguous")
    executor = ToolExecutor(ExplodingSandbox(), idempotency_store=idem, intent_store=intents)

    calls = 0
    async def resolver(found):
        nonlocal calls
        calls += 1
        assert found.idempotency_key == "k"
        return ToolResult("c", "remote_write", True, {"remote_id": "42"}, idempotency_key="k")

    result = await executor.reconcile_intent(intent, resolver)
    assert result.ok and calls == 1
    assert intents.get("k").state == "completed"
    assert idem.get("k").value == {"remote_id": "42"}
