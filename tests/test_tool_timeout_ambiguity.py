import asyncio
import pytest

from runtime.tool_executor import ToolExecutor
from runtime.tool_idempotency_store import ToolIdempotencyStore
from runtime.tool_intent_store import ToolIntentStore
from runtime.tool_protocol import ToolCall
from runtime.tool_sandbox import ToolExecutionContext, ToolSandbox


class SlowSandbox(ToolSandbox):
    async def execute(self, call, context, execution_context=None):
        await asyncio.sleep(0.05)
        return "late"


@pytest.mark.asyncio
async def test_timeout_is_ambiguous_and_not_retryable(tmp_path):
    intents = ToolIntentStore(str(tmp_path / "intents.json"))
    results = ToolIdempotencyStore(str(tmp_path / "results.json"))
    executor = ToolExecutor(SlowSandbox(), idempotency_store=results, intent_store=intents)
    call = ToolCall("remote_write", {}, "call-1", timeout=0.001, idempotency_key="k")

    result = await executor.execute(call, ToolExecutionContext(agent_id="a"))

    assert result.ok is False
    assert result.retryable is False
    assert intents.get("k").state == "ambiguous"
    assert results.get("k") is None
