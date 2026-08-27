"""Timeout/cancellation aware execution of typed tool calls."""

import asyncio

from .event_bus import EventBus
from .execution_context import ExecutionContext
from .execution_events import ExecutionEvent
from .event_types import TOOL_COMPLETED, TOOL_FAILED, TOOL_STARTED
from .tool_idempotency_store import StoredToolResult, ToolIdempotencyStore
from .tool_protocol import ToolCall, ToolResult
from .tool_sandbox import ToolExecutionContext, ToolSandbox


class ToolExecutor:
    def __init__(self, sandbox: ToolSandbox, event_bus: EventBus | None = None, idempotency_store: ToolIdempotencyStore | None = None):
        self.sandbox = sandbox
        self.event_bus = event_bus
        self.idempotency_store = idempotency_store

    async def execute(self, call: ToolCall, context: ToolExecutionContext, execution_context: ExecutionContext | None = None) -> ToolResult:
        ctx = execution_context or ExecutionContext(agent_id=context.agent_id)
        if self.idempotency_store and call.idempotency_key:
            stored = self.idempotency_store.get(call.idempotency_key)
            if stored:
                return ToolResult(call.call_id, call.tool, stored.ok, stored.value, stored.error, False, stored.idempotency_key)
        await self._publish(TOOL_STARTED, ctx, {"tool": call.tool, "call_id": call.call_id, "idempotency_key": call.idempotency_key})
        try:
            operation = self.sandbox.execute(call.tool, context, **call.arguments)
            value = await asyncio.wait_for(operation, timeout=call.timeout) if call.timeout is not None else await operation
            result = ToolResult.success(call, value)
            if self.idempotency_store and call.idempotency_key:
                stored = self.idempotency_store.put_if_absent(StoredToolResult(call.idempotency_key, call.call_id, call.tool, True, value=value))
                result = ToolResult(call.call_id, call.tool, stored.ok, stored.value, stored.error, False, stored.idempotency_key)
            await self._publish(TOOL_COMPLETED, ctx, {"tool": call.tool, "call_id": call.call_id, "idempotency_key": call.idempotency_key})
            return result
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            retryable = isinstance(exc, (asyncio.TimeoutError, TimeoutError, ConnectionError, OSError))
            result = ToolResult.failure(call, exc, retryable=retryable)
            await self._publish(TOOL_FAILED, ctx, {"tool": call.tool, "call_id": call.call_id, "error": str(exc), "retryable": retryable, "idempotency_key": call.idempotency_key})
            return result

    async def _publish(self, event_type: str, context: ExecutionContext, data: dict):
        if self.event_bus:
            await self.event_bus.publish(event_type, ExecutionEvent(event_type, context, data))
