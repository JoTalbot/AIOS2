import pytest

from runtime.execution_context import ExecutionContext
from runtime.tool_executor import ToolExecutor
from runtime.tool_idempotency_store import StoredToolResult, ToolIdempotencyStore
from runtime.tool_protocol import ToolCall, ToolResult
from runtime.tool_registry import ToolRegistry
from runtime.tool_sandbox import ToolBoundaryError, ToolExecutionContext, ToolSandbox


@pytest.mark.asyncio
async def test_retryable_failure_does_not_cache_and_allows_retry(tmp_path):
    calls = []

    def flaky(value):
        calls.append(value)
        if len(calls) == 1:
            raise RuntimeError("transient")
        return value * 2

    registry = ToolRegistry()
    registry.register("flaky", flaky)
    results = ToolIdempotencyStore(str(tmp_path / "results.json"))
    executor = ToolExecutor(ToolSandbox(registry, authorization={"agent": set()}), idempotency_store=results)
    context = ToolExecutionContext("agent")
    execution_context = ExecutionContext(agent_id="agent", execution_id="e1")
    call = ToolCall("flaky", {"value": 21}, call_id="c1", idempotency_key="k1")

    first = await executor.execute(call, context, execution_context)
    second = await executor.execute(call, context, execution_context)

    assert isinstance(first, ToolResult)
    assert first.retryable
    assert not first.ambiguous
    assert second.ok
    assert second.value == 42
    assert calls == [21, 21]
    assert results.get("k1") is not None
    assert results.get("k1").value == 42


@pytest.mark.asyncio
async def test_success_after_retry_is_reused_without_second_side_effect(tmp_path):
    calls = []
    registry = ToolRegistry()
    registry.register("write", lambda value: calls.append(value) or value)
    results = ToolIdempotencyStore(str(tmp_path / "results.json"))
    executor = ToolExecutor(ToolSandbox(registry, authorization={"agent": set()}), idempotency_store=results)
    context = ToolExecutionContext("agent")
    execution_context = ExecutionContext(agent_id="agent", execution_id="e1")
    call = ToolCall("write", {"value": 7}, call_id="c1", idempotency_key="k1")

    first = await executor.execute(call, context, execution_context)
    second = await executor.execute(call, context, execution_context)

    assert first.ok and second.ok
    assert second.value == 7
    assert calls == [7]


@pytest.mark.asyncio
async def test_same_idempotency_key_with_different_arguments_is_rejected(tmp_path):
    calls = []
    registry = ToolRegistry()
    registry.register("write", lambda value: calls.append(value) or value)
    results = ToolIdempotencyStore(str(tmp_path / "results.json"))
    results.put_if_absent(StoredToolResult("k1", "c1", "write", True, 7, None, {"value": 7}))
    executor = ToolExecutor(ToolSandbox(registry, authorization={"agent": set()}), idempotency_store=results)
    context = ToolExecutionContext("agent")
    execution_context = ExecutionContext(agent_id="agent", execution_id="e1")
    conflicting = ToolCall("write", {"value": 8}, call_id="c1", idempotency_key="k1")

    with pytest.raises(ToolBoundaryError, match="idempotency key conflicts"):
        await executor.execute(conflicting, context, execution_context)

    assert calls == []
