import asyncio
import pytest

from runtime.tool_executor import ToolExecutor
from runtime.tool_idempotency_store import ToolIdempotencyStore
from runtime.tool_intent_store import ToolIntentStore
from runtime.tool_protocol import ToolCall
from runtime.tool_sandbox import ToolExecutionContext, ToolSandbox
from runtime.tool_registry import ToolRegistry


@pytest.mark.asyncio
async def test_timeout_is_ambiguous_and_not_retryable(tmp_path):
    async def slow():
        await asyncio.sleep(10)
    registry = ToolRegistry(); registry.register("slow", slow)
    executor = ToolExecutor(
        ToolSandbox(registry=registry, authorization={"a": frozenset()}),
        idempotency_store=ToolIdempotencyStore(tmp_path / "idem.json"),
        intent_store=ToolIntentStore(tmp_path / "intent.json"),
    )
    result = await executor.execute(
        ToolCall(tool="slow", arguments={}, idempotency_key="timeout", timeout=0.01),
        ToolExecutionContext("a"),
    )
    assert result.ok is False
    assert result.retryable is False
    assert executor.intent_store.get("timeout").state == "ambiguous"


@pytest.mark.asyncio
async def test_concurrent_unique_keys_do_not_share_results(tmp_path):
    calls = []
    async def echo(value):
        calls.append(value)
        await asyncio.sleep(0)
        return value
    registry = ToolRegistry(); registry.register("echo", echo)
    executor = ToolExecutor(
        ToolSandbox(registry=registry, authorization={"a": frozenset()}),
        idempotency_store=ToolIdempotencyStore(tmp_path / "idem.json"),
        intent_store=ToolIntentStore(tmp_path / "intent.json"),
    )
    results = await asyncio.gather(*[
        executor.execute(ToolCall(tool="echo", arguments={"value": i}, idempotency_key=f"k-{i}"), ToolExecutionContext("a"))
        for i in range(25)
    ])
    assert [r.value for r in results] == list(range(25))
    assert sorted(calls) == list(range(25))
