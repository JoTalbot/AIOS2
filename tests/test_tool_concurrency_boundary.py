import asyncio

import pytest

from runtime.tool_idempotency_store import ToolIdempotencyStore
from runtime.tool_intent_store import ToolIntentStore
from runtime.tool_protocol import ToolCall
from runtime.tool_registry import ToolRegistry
from runtime.tool_sandbox import ToolExecutionContext, ToolSandbox
from runtime.tool_executor import ToolExecutor


@pytest.mark.asyncio
async def test_concurrent_same_key_has_single_side_effect(tmp_path):
    calls = 0

    async def handler():
        nonlocal calls
        calls += 1
        await asyncio.sleep(0.01)
        return "ok"

    registry = ToolRegistry()
    registry.register("safe", handler)
    sandbox = ToolSandbox(registry=registry, authorization={"agent": set()})
    executor = ToolExecutor(
        sandbox,
        idempotency_store=ToolIdempotencyStore(str(tmp_path / "results.json")),
        intent_store=ToolIntentStore(str(tmp_path / "intents.json"), claim_ttl_seconds=2),
    )
    call = ToolCall(tool="safe", arguments={}, idempotency_key="same")
    ctx = ToolExecutionContext("agent")
    results = await asyncio.gather(*(executor.execute(call, ctx) for _ in range(20)))
    assert calls == 1
    assert all(result.ok for result in results)


@pytest.mark.asyncio
async def test_long_running_claim_is_renewed(tmp_path):
    started = asyncio.Event()

    async def handler():
        started.set()
        await asyncio.sleep(0.08)
        return "ok"

    registry = ToolRegistry()
    registry.register("slow", handler)
    sandbox = ToolSandbox(registry=registry, authorization={"agent": set()})
    executor = ToolExecutor(
        sandbox,
        intent_store=ToolIntentStore(str(tmp_path / "intents.json"), claim_ttl_seconds=1),
    )
    task = asyncio.create_task(executor.execute(ToolCall(tool="slow", idempotency_key="k"), ToolExecutionContext("agent")))
    await started.wait()
    await task
    intent = executor.intent_store.get("k")
    assert intent.state == "completed"
