import asyncio

import pytest

from runtime.tool_executor import ToolExecutor
from runtime.tool_protocol import ToolCall
from runtime.tool_sandbox import ToolBoundaryError, ToolExecutionContext, ToolSandbox
from runtime.tool_registry import ToolPermissionError, ToolRegistry


@pytest.mark.asyncio
async def test_sandbox_does_not_trust_caller_permissions():
    registry = ToolRegistry()
    registry.register("privileged", lambda: "ok", permissions={"network.write"})
    sandbox = ToolSandbox(registry=registry)

    with pytest.raises(ToolPermissionError):
        await sandbox.execute(
            ToolCall("privileged"),
            ToolExecutionContext("agent-1", frozenset({"network.write"})),
        )


@pytest.mark.asyncio
async def test_sandbox_uses_server_side_authorization():
    registry = ToolRegistry()
    registry.register("privileged", lambda: "ok", permissions={"network.write"})
    sandbox = ToolSandbox(
        registry=registry,
        authorization={"agent-1": {"network.write"}},
    )

    result = await sandbox.execute(
        ToolCall("privileged"),
        ToolExecutionContext("agent-1", frozenset({"network.write"})),
    )
    assert result == "ok"


@pytest.mark.asyncio
async def test_sandbox_rejects_untyped_or_invalid_context():
    sandbox = ToolSandbox()
    with pytest.raises(ToolBoundaryError):
        await sandbox.execute("echo", object())


@pytest.mark.asyncio
async def test_executor_marks_cancelled_side_effect_as_ambiguous(tmp_path):
    registry = ToolRegistry()
    started = asyncio.Event()

    async def slow_tool():
        started.set()
        await asyncio.sleep(60)

    registry.register("slow", slow_tool)
    sandbox = ToolSandbox(registry=registry)

    from runtime.tool_intent_store import ToolIntentStore

    intent_store = ToolIntentStore(tmp_path / "intents.json")
    executor = ToolExecutor(sandbox, intent_store=intent_store)
    call = ToolCall("slow", call_id="c1", idempotency_key="idem-1")
    task = asyncio.create_task(
        executor.execute(call, ToolExecutionContext("agent-1"))
    )
    await started.wait()
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task

    intent = intent_store.get("idem-1")
    assert intent is not None
    assert intent.state == "ambiguous"
