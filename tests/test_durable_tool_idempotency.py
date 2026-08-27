import pytest

from runtime.execution_context import ExecutionContext
from runtime.tool_executor import ToolExecutor
from runtime.tool_idempotency_store import StoredToolResult, ToolIdempotencyStore
from runtime.tool_protocol import ToolCall
from runtime.tool_registry import ToolRegistry
from runtime.tool_sandbox import ToolExecutionContext, ToolSandbox


def test_result_survives_executor_restart(tmp_path):
    path = tmp_path / "tool-idempotency.json"
    calls = []
    registry = ToolRegistry()

    def effect(value):
        calls.append(value)
        return value

    registry.register("write", effect)
    store = ToolIdempotencyStore(str(path))
    call = ToolCall("write", {"value": 7}, call_id="c1", idempotency_key="e1:0")
    ctx = ToolExecutionContext("agent")

    first = __import__("asyncio").run(ToolExecutor(ToolSandbox(registry, authorization={"agent": set()}), idempotency_store=store).execute(call, ctx, ExecutionContext(agent_id="agent")))
    second = __import__("asyncio").run(ToolExecutor(ToolSandbox(registry, authorization={"agent": set()}), idempotency_store=ToolIdempotencyStore(str(path))).execute(call, ctx, ExecutionContext(agent_id="agent")))

    assert first.ok and second.ok
    assert first.value == second.value == 7
    assert calls == [7]


def test_concurrent_put_if_absent_keeps_one_record(tmp_path):
    store = ToolIdempotencyStore(str(tmp_path / "tool-idempotency.json"))
    first = StoredToolResult("k", "c1", "tool", True, "first")
    second = StoredToolResult("k", "c2", "tool", True, "second")
    assert store.put_if_absent(first) == first
    assert store.put_if_absent(second) == first
    assert store.get("k") == first
