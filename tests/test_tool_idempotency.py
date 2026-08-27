import pytest

from runtime.execution_context import ExecutionContext
from runtime.tool_executor import ToolExecutor
from runtime.tool_protocol import ToolCall
from runtime.tool_registry import ToolRegistry
from runtime.tool_sandbox import ToolSandbox, ToolExecutionContext


@pytest.mark.asyncio
async def test_successful_idempotent_call_executes_once():
    calls = []
    registry = ToolRegistry()

    def side_effect(value):
        calls.append(value)
        return value

    registry.register("write", side_effect)
    executor = ToolExecutor(ToolSandbox(registry, authorization={"agent": set()}))
    context = ToolExecutionContext("agent")
    call = ToolCall("write", {"value": 42}, call_id="a", idempotency_key="exec-1:0")

    first = await executor.execute(call, context, ExecutionContext(agent_id="agent"))
    second = await executor.execute(call, context, ExecutionContext(agent_id="agent"))

    assert first.ok and second.ok
    assert first.value == second.value == 42
    assert calls == [42]


@pytest.mark.asyncio
async def test_failed_idempotent_call_can_retry():
    attempts = []
    registry = ToolRegistry()

    def flaky():
        attempts.append(1)
        if len(attempts) == 1:
            raise ConnectionError("temporary")
        return "ok"

    registry.register("flaky", flaky)
    executor = ToolExecutor(ToolSandbox(registry, authorization={"agent": set()}))
    context = ToolExecutionContext("agent")
    call = ToolCall("flaky", call_id="a", idempotency_key="exec-2:0")

    first = await executor.execute(call, context)
    second = await executor.execute(call, context)

    assert not first.ok and first.retryable
    assert second.ok and second.value == "ok"
    assert len(attempts) == 2
