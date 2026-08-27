"""Timeout/cancellation aware execution of typed tool calls."""

import asyncio
from typing import Dict

from .event_bus import EventBus
from .execution_context import ExecutionContext
from .execution_events import ExecutionEvent
from .event_types import TOOL_COMPLETED, TOOL_FAILED, TOOL_STARTED
from .tool_protocol import ToolCall, ToolResult
from .tool_sandbox import ToolExecutionContext, ToolSandbox


class ToolExecutor:
    def __init__(self, sandbox: ToolSandbox, event_bus: EventBus | None = None):
        self.sandbox = sandbox
        self.event_bus = event_bus
        self._idempotent_results: Dict[str, ToolResult] = {}
        self._idempotent_locks: Dict[str, asyncio.Lock] = {}

    async def execute(self, call: ToolCall, context: ToolExecutionContext, execution_context: ExecutionContext | None = None) -> ToolResult:
        key = call.idempotency_key
        if key:
            lock = self._idempotent_locks.setdefault(key, asyncio.Lock())
            async with lock:
                cached = self._idempotent_results.get(key)
                if cached is not None:
                    return cached
                result = await self._execute_once(call, context, execution_context)
                if result.ok:
                    self._idempotent_results[key] = result
                return result
        return await self._execute_once(call, context, execution_context)

    async def _execute_once(self, call: ToolCall, context: ToolExecutionContext, execution_context: ExecutionContext | None = None) -> ToolResult:
        ctx = execution_context or ExecutionContext(agent_id=context.agent_id)
        await self._publish(TOOL_STARTED, ctx, {"tool": call.tool, "call_id": call.call_id})
        try:
            operation = self.sandbox.execute(call.tool, context, **call.arguments)
            if call.timeout is not None:
                value = await asyncio.wait_for(operation, timeout=call.timeout)
            else:
                value = await operation
            result = ToolResult.success(call, value)
            await self._publish(TOOL_COMPLETED, ctx, {"tool": call.tool, "call_id": call.call_id})
            return result
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            retryable = isinstance(exc, (asyncio.TimeoutError, TimeoutError, ConnectionError, OSError))
            result = ToolResult.failure(call, exc, retryable=retryable)
            await self._publish(TOOL_FAILED, ctx, {"tool": call.tool, "call_id": call.call_id, "error": str(exc), "retryable": retryable})
            return result

    async def _publish(self, event_type: str, context: ExecutionContext, data: dict):
        if self.event_bus:
            await self.event_bus.publish(event_type, ExecutionEvent(event_type, context, data))
