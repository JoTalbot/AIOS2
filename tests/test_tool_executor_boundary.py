import pytest

from runtime.execution_context import ExecutionContext
from runtime.tool_executor import ToolExecutor
from runtime.tool_idempotency_store import ToolIdempotencyStore
from runtime.tool_intent_store import ToolIntentStore
from runtime.tool_protocol import ToolCall
from runtime.tool_registry import ToolRegistry
from runtime.tool_sandbox import ToolSandbox, ToolExecutionContext


@pytest.mark.asyncio
async def test_terminal_result_stays_durable_when_claim_is_lost(tmp_path):
    registry = ToolRegistry()
    registry.register("write", lambda value: value)
    intents = ToolIntentStore(str(tmp_path / "intents.json"))
    results = ToolIdempotencyStore(str(tmp_path / "results.json"))
    executor = ToolExecutor(
        ToolSandbox(registry, authorization={"agent": set()}),
        idempotency_store=results,
        intent_store=intents,
    )
    call = ToolCall("write", {"value": 42}, call_id="c1", idempotency_key="k1")
    boundary = executor.execution_boundary
    assert boundary is not None

    boundary.boundary.intents.mark_claimed = lambda *args, **kwargs: None

    returned = await executor.execute(
        call,
        ToolExecutionContext("agent"),
        ExecutionContext(agent_id="agent", execution_id="e1"),
    )

    assert returned.ok
    assert returned.ambiguous
    assert results.get("k1").value == 42
    assert intents.get("k1").state == "executing"
