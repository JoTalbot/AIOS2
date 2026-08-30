import asyncio

import pytest

from runtime.execution_context import ExecutionContext
from runtime.tool_executor import ToolExecutor
from runtime.tool_idempotency_store import ToolIdempotencyStore
from runtime.tool_intent_store import ToolIntentStore
from runtime.tool_protocol import ToolCall
from runtime.tool_registry import ToolRegistry
from runtime.tool_sandbox import ToolSandbox, ToolExecutionContext


@pytest.mark.asyncio
async def test_cancellation_after_side_effect_marks_intent_ambiguous(tmp_path):
    calls = []
    started = asyncio.Event()
    release = asyncio.Event()

    async def charge(value):
        calls.append(value)
        started.set()
        await release.wait()
        return value

    registry = ToolRegistry()
    registry.register("charge", charge)
    intents = ToolIntentStore(str(tmp_path / "intents.json"))
    results = ToolIdempotencyStore(str(tmp_path / "results.json"))
    sandbox = ToolSandbox(registry, authorization={"agent": set()})
    executor = ToolExecutor(sandbox, idempotency_store=results, intent_store=intents)
    call = ToolCall("charge", {"value": 10}, call_id="c1", idempotency_key="k1")
    context = ToolExecutionContext("agent")
    execution_context = ExecutionContext(agent_id="agent", execution_id="e1")

    task = asyncio.create_task(executor.execute(call, context, execution_context))
    await started.wait()
    task.cancel()

    with pytest.raises(asyncio.CancelledError):
        await task

    intent = intents.get("k1")
    assert calls == [10]
    assert intent is not None
    assert intent.state == "ambiguous"
    assert results.get("k1") is None
