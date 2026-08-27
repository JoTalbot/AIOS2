"""Timeout/cancellation aware execution of typed tool calls."""

import asyncio
import uuid
from typing import Dict

from .event_bus import EventBus
from .execution_context import ExecutionContext
from .execution_events import ExecutionEvent
from .event_types import TOOL_COMPLETED, TOOL_FAILED, TOOL_STARTED
from .tool_idempotency_store import StoredToolResult, ToolIdempotencyStore
from .tool_intent_store import ToolIntent, ToolIntentStore
from .tool_protocol import ToolCall, ToolResult
from .tool_sandbox import ToolExecutionContext, ToolSandbox


class ToolExecutor:
    def __init__(self, sandbox: ToolSandbox, event_bus: EventBus | None = None,
                 idempotency_store: ToolIdempotencyStore | None = None,
                 intent_store: ToolIntentStore | None = None):
        self.sandbox = sandbox
        self.event_bus = event_bus
        self.idempotency_store = idempotency_store
        self.intent_store = intent_store
        self._idempotent_results: Dict[str, ToolResult] = {}
        self._idempotent_locks: Dict[str, asyncio.Lock] = {}

    async def execute(self, call: ToolCall, context: ToolExecutionContext,
                      execution_context: ExecutionContext | None = None) -> ToolResult:
        key = call.idempotency_key
        if key:
            lock = self._idempotent_locks.setdefault(key, asyncio.Lock())
            async with lock:
                cached = self._idempotent_results.get(key)
                if cached is not None:
                    return cached
                if self.idempotency_store:
                    stored = self.idempotency_store.get(key)
                    if stored:
                        result = ToolResult(call.call_id, call.tool, stored.ok, stored.value,
                                            stored.error, False, stored.idempotency_key)
                        self._idempotent_results[key] = result
                        return result
                claim_owner = f"executor:{uuid.uuid4().hex}"
                claim_token = uuid.uuid4().hex
                if self.intent_store:
                    intent = self.intent_store.prepare(ToolIntent(
                        key, call.call_id, call.tool, call.arguments,
                        getattr(execution_context, "execution_id", None)))
                    if intent.state == "completed" and self.idempotency_store:
                        stored = self.idempotency_store.get(key)
                        if stored:
                            result = ToolResult(call.call_id, call.tool, stored.ok, stored.value,
                                                stored.error, False, stored.idempotency_key)
                            self._idempotent_results[key] = result
                            return result
                    claimed = self.intent_store.claim(key, claim_owner, claim_token)
                    if claimed is None:
                        current = self.intent_store.get(key)
                        if current and current.state == "completed" and self.idempotency_store:
                            stored = self.idempotency_store.get(key)
                            if stored:
                                result = ToolResult(call.call_id, call.tool, stored.ok, stored.value,
                                                    stored.error, False, stored.idempotency_key)
                                self._idempotent_results[key] = result
                                return result
                        return ToolResult.failure(call, RuntimeError("intent is already claimed"))
                try:
                    result = await self._execute_once(call, context, execution_context)
                    if result.ok:
                        if self.idempotency_store:
                            stored = self.idempotency_store.put_if_absent(
                                StoredToolResult(key, call.call_id, call.tool, True, result.value))
                            result = ToolResult(call.call_id, call.tool, stored.ok, stored.value,
                                                stored.error, False, stored.idempotency_key)
                        if self.intent_store:
                            self.intent_store.mark_claimed(key, claim_owner, claim_token, "completed")
                        self._idempotent_results[key] = result
                    elif self.intent_store:
                        self.intent_store.release_claim(key, claim_owner, claim_token, "ambiguous")
                    return result
                except asyncio.CancelledError:
                    if self.intent_store:
                        self.intent_store.release_claim(key, claim_owner, claim_token, "ambiguous")
                    raise
        return await self._execute_once(call, context, execution_context)

    async def reconcile_intent(self, intent: ToolIntent, resolver):
        """Resolve an ambiguous operation without replaying its side effect.

        Terminal intent transitions belong to the recovery worker, which owns the
        fencing token. This method only resolves and persists the idempotent result.
        """
        if self.idempotency_store:
            stored = self.idempotency_store.get(intent.idempotency_key)
            if stored:
                return ToolResult(intent.call_id, intent.tool, stored.ok, stored.value,
                                  stored.error, False, stored.idempotency_key)
        result = resolver(intent)
        if hasattr(result, "__await__"):
            result = await result
        if result is None:
            return None
        if not isinstance(result, ToolResult):
            raise TypeError("resolver must return ToolResult or None")
        if result.ok and self.idempotency_store:
            self.idempotency_store.put_if_absent(
                StoredToolResult(intent.idempotency_key, intent.call_id, intent.tool, True, result.value))
        return result

    async def _execute_once(self, call: ToolCall, context: ToolExecutionContext,
                            execution_context: ExecutionContext | None = None) -> ToolResult:
        ctx = execution_context or ExecutionContext(agent_id=context.agent_id)
        await self._publish(TOOL_STARTED, ctx, {"tool": call.tool, "call_id": call.call_id,
                                                "idempotency_key": call.idempotency_key})
        try:
            operation = self.sandbox.execute(call.tool, context, **call.arguments)
            value = await asyncio.wait_for(operation, timeout=call.timeout) if call.timeout is not None else await operation
            result = ToolResult.success(call, value)
            await self._publish(TOOL_COMPLETED, ctx, {"tool": call.tool, "call_id": call.call_id,
                                                      "idempotency_key": call.idempotency_key})
            return result
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            retryable = isinstance(exc, (asyncio.TimeoutError, TimeoutError, ConnectionError, OSError))
            result = ToolResult.failure(call, exc, retryable=retryable)
            await self._publish(TOOL_FAILED, ctx, {"tool": call.tool, "call_id": call.call_id,
                                                   "error": str(exc), "retryable": retryable,
                                                   "idempotency_key": call.idempotency_key})
            return result

    async def _publish(self, event_type: str, context: ExecutionContext, data: dict):
        if self.event_bus:
            await self.event_bus.publish(event_type, ExecutionEvent(event_type, context, data))
