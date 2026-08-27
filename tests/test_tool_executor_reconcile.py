import asyncio

import pytest

from runtime.tool_executor import ToolExecutor
from runtime.tool_intent_store import ToolIntent, ToolIntentStore
from runtime.tool_protocol import ToolCall, ToolResult


class DummySandbox:
    pass


def call():
    return ToolCall(call_id="c1", tool="write", arguments={}, idempotency_key="k")


@pytest.mark.asyncio
async def test_reconcile_none_does_not_claim_resolution():
    executor = ToolExecutor(DummySandbox())
    intent = type("Intent", (), {"idempotency_key": "k", "call_id": "c1", "tool": "write"})()
    assert await executor.reconcile_intent(intent, lambda _: None) is None


@pytest.mark.asyncio
async def test_reconcile_failure_is_returned_without_persisting_success():
    executor = ToolExecutor(DummySandbox())
    intent = type("Intent", (), {"idempotency_key": "k", "call_id": "c1", "tool": "write"})()
    result = ToolResult.failure(call(), RuntimeError("unresolved"), retryable=True)
    assert await executor.reconcile_intent(intent, lambda _: result) is result


@pytest.mark.asyncio
async def test_reconcile_success_returns_result_and_persists_when_store_present(tmp_path):
    class Store:
        def __init__(self): self.saved = []
        def get(self, key): return None
        def put_if_absent(self, value): self.saved.append(value); return value

    store = Store()
    executor = ToolExecutor(DummySandbox(), idempotency_store=store)
    intent = type("Intent", (), {"idempotency_key": "k", "call_id": "c1", "tool": "write"})()
    result = ToolResult.success(call(), {"resolved": True})
    resolved = await executor.reconcile_intent(intent, lambda _: result)
    assert resolved is result
    assert len(store.saved) == 1
    assert store.saved[0].idempotency_key == "k"


@pytest.mark.asyncio
async def test_reconcile_success_finalizes_unclaimed_intent(tmp_path):
    path = tmp_path / "intents.json"
    intent = ToolIntent("k", "c1", "write", {}, state="ambiguous")
    store = ToolIntentStore(str(path)); store.prepare(intent)
    executor = ToolExecutor(DummySandbox(), intent_store=store)
    result = ToolResult.success(call(), "resolved")
    assert await executor.reconcile_intent(intent, lambda _: result) is result
    assert store.get("k").state == "completed"


@pytest.mark.asyncio
async def test_reconcile_supports_async_resolver():
    executor = ToolExecutor(DummySandbox())
    intent = type("Intent", (), {"idempotency_key": "k", "call_id": "c1", "tool": "write"})()

    async def resolver(_):
        await asyncio.sleep(0)
        return ToolResult.success(call(), "resolved")

    result = await executor.reconcile_intent(intent, resolver)
    assert result.value == "resolved"


@pytest.mark.asyncio
async def test_reconcile_rejects_invalid_resolver_result():
    executor = ToolExecutor(DummySandbox())
    intent = type("Intent", (), {"idempotency_key": "k", "call_id": "c1", "tool": "write"})()
    with pytest.raises(TypeError):
        await executor.reconcile_intent(intent, lambda _: "not-a-tool-result")
