from runtime.execution_context import ExecutionContext
from runtime.tool_executor import ToolExecutor
from runtime.tool_idempotency_store import ToolIdempotencyStore
from runtime.tool_intent_store import ToolIntentStore
from runtime.tool_protocol import ToolCall
from runtime.tool_registry import ToolRegistry
from runtime.tool_sandbox import ToolSandbox, ToolExecutionContext


async def test_second_worker_reuses_durable_result_after_first_worker_loses_claim(tmp_path):
    calls = []
    registry = ToolRegistry()
    registry.register("write", lambda value: calls.append(value) or value)
    intents = ToolIntentStore(str(tmp_path / "intents.json"))
    results = ToolIdempotencyStore(str(tmp_path / "results.json"))
    sandbox = ToolSandbox(registry, authorization={"agent": set()})
    call = ToolCall("write", {"value": 42}, call_id="c1", idempotency_key="k1")
    context = ToolExecutionContext("agent")
    execution_context = ExecutionContext(agent_id="agent", execution_id="e1")

    first = ToolExecutor(sandbox, idempotency_store=results, intent_store=intents)
    assert first.execution_boundary is not None
    first.execution_boundary.boundary.intents.mark_claimed = lambda *args, **kwargs: None

    lost_claim = await first.execute(call, context, execution_context)
    assert lost_claim.ok
    assert lost_claim.ambiguous
    assert calls == [42]

    second = ToolExecutor(sandbox, idempotency_store=results, intent_store=intents)
    recovered = await second.execute(call, context, execution_context)

    assert recovered.ok
    assert not recovered.ambiguous
    assert recovered.value == 42
    assert calls == [42]
