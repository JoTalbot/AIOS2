import asyncio

import pytest

from runtime.tool_idempotency_store import StoredToolResult, ToolIdempotencyStore
from runtime.tool_protocol import ToolCall
from runtime.tool_registry import ToolPermissionError, ToolRegistry
from runtime.tool_sandbox import ToolBoundaryError, ToolExecutionContext, ToolSandbox


@pytest.mark.asyncio
async def test_sandbox_does_not_trust_caller_permissions():
    registry = ToolRegistry()
    registry.register("danger", lambda: "ok", permissions={"dangerous"})
    sandbox = ToolSandbox(registry=registry, authorization={"agent": set()})
    with pytest.raises(ToolPermissionError):
        await sandbox.execute("danger", ToolExecutionContext("agent", frozenset({"dangerous"})))


@pytest.mark.asyncio
async def test_sandbox_intersects_claimed_permissions_with_authorization():
    registry = ToolRegistry()
    registry.register("safe", lambda: "ok", permissions={"safe"})
    sandbox = ToolSandbox(registry=registry, authorization={"agent": {"safe"}})
    result = await sandbox.execute("safe", ToolExecutionContext("agent", frozenset({"safe", "other"})))
    assert result == "ok"


def test_idempotency_key_cannot_bind_two_calls(tmp_path):
    store = ToolIdempotencyStore(str(tmp_path / "idempotency.json"))
    store.put_if_absent(StoredToolResult("k", "call-1", "safe", True, "ok"))
    with pytest.raises(ValueError):
        store.put_if_absent(StoredToolResult("k", "call-2", "danger", True, "bad"))


def test_idempotency_store_persists_atomically(tmp_path):
    path = tmp_path / "idempotency.json"
    store = ToolIdempotencyStore(str(path))
    store.put_if_absent(StoredToolResult("k", "call-1", "safe", True, {"value": 1}))
    assert ToolIdempotencyStore(str(path)).get("k").value == {"value": 1}


@pytest.mark.asyncio
async def test_sandbox_rejects_argument_override_for_typed_call():
    sandbox = ToolSandbox()
    call = ToolCall(tool="safe", arguments={"x": 1})
    with pytest.raises(ToolBoundaryError):
        await sandbox.execute(call, ToolExecutionContext("agent"), x=2)
