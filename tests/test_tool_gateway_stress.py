import asyncio
import json

import pytest

from runtime.tool_executor import ToolExecutor
from runtime.tool_gateway import ToolGateway
from runtime.tool_idempotency_store import ToolIdempotencyStore
from runtime.tool_intent_store import ToolIntentStore
from runtime.tool_protocol import ToolCall
from runtime.tool_sandbox import ToolExecutionContext, ToolSandbox
from runtime.tool_registry import ToolRegistry


@pytest.mark.asyncio
async def test_same_key_concurrent_calls_execute_once(tmp_path):
    calls = 0
    gate = asyncio.Event()

    async def handler(value):
        nonlocal calls
        calls += 1
        await gate.wait()
        return value

    registry = ToolRegistry()
    registry.register("echo", handler)
    sandbox = ToolSandbox(registry=registry, authorization={"agent": frozenset()})
    executor = ToolExecutor(
        sandbox,
        idempotency_store=ToolIdempotencyStore(tmp_path / "idem.json"),
        intent_store=ToolIntentStore(tmp_path / "intent.json"),
    )
    gateway = ToolGateway(executor)
    context = ToolExecutionContext("agent")
    call = ToolCall(tool="echo", arguments={"value": "ok"}, idempotency_key="same")

    tasks = [asyncio.create_task(gateway.execute(call, context)) for _ in range(10)]
    await asyncio.sleep(0)
    gate.set()
    results = await asyncio.gather(*tasks)

    assert calls == 1
    assert all(result.ok and result.value == "ok" for result in results)


@pytest.mark.asyncio
async def test_claim_loss_fails_closed(tmp_path):
    started = asyncio.Event()
    release = asyncio.Event()

    async def handler():
        started.set()
        await release.wait()
        return "done"

    registry = ToolRegistry()
    registry.register("slow", handler)
    intent_store = ToolIntentStore(tmp_path / "intent.json", claim_ttl_seconds=1)
    executor = ToolExecutor(
        ToolSandbox(registry=registry, authorization={"agent": frozenset()}),
        idempotency_store=ToolIdempotencyStore(tmp_path / "idem.json"),
        intent_store=intent_store,
    )
    task = asyncio.create_task(executor.execute(
        ToolCall(tool="slow", arguments={}, idempotency_key="k"),
        ToolExecutionContext("agent"),
    ))
    await started.wait()
    raw = json.loads(intent_store.path.read_text())
    raw["k"]["claim_expires_at"] = "2000-01-01T00:00:00+00:00"
    intent_store.path.write_text(json.dumps(raw))
    await asyncio.sleep(0.5)
    release.set()
    result = await task
    # Main's design: a tool that completed after its claim was lost is
    # reported as AMBIGUOUS, never as a silently clean success, and is not
    # retryable. (Stricter fail-closed semantics tracked in the backlog.)
    assert result.ambiguous is True
    assert result.retryable is False
