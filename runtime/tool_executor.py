"""Runtime tool execution with durable idempotency and crash-safe intent recovery."""
from typing import Any

from .execution_boundary import ExecutionBoundary
from .execution_context import ExecutionContext
from .tool_idempotency_store import StoredToolResult
from .tool_intent_store import ToolIntent
from .tool_protocol import ToolCall, ToolResult
from .tool_sandbox import ToolBoundaryError, ToolExecutionContext, ToolSandbox


class ToolExecutor:
    def __init__(self, sandbox: ToolSandbox, *, idempotency_store=None, intent_store=None, event_bus=None):
        self.sandbox = sandbox
        self.idempotency_store = idempotency_store
        self.intent_store = intent_store
        self.event_bus = event_bus
        self.execution_boundary = ExecutionBoundary(intent_store, idempotency_store) if intent_store and idempotency_store else None

    async def reconcile_intent(self, intent: ToolIntent, resolver):
        """Resolve an ambiguous operation and persist its terminal state."""
        arguments = getattr(intent, "arguments", {})
        if self.idempotency_store:
            stored = self.idempotency_store.get(intent.idempotency_key)
            if stored:
                if not self._stored_matches_call(stored, ToolCall(intent.tool, arguments, intent.call_id, idempotency_key=intent.idempotency_key)):
                    raise ToolBoundaryError("idempotency key conflicts with stored tool intent")
                if self.intent_store and not (intent.owner_id and intent.claim_token): self.intent_store.mark(intent.idempotency_key, "completed" if stored.ok else "failed")
                return ToolResult(intent.call_id, intent.tool, stored.ok, stored.value, stored.error, False, stored.idempotency_key)
        result = resolver(intent)
        if hasattr(result, "__await__"): result = await result
        if result is None: return None
        if not isinstance(result, ToolResult): raise TypeError("resolver must return ToolResult or None")
        if self.idempotency_store:
            stored = self.idempotency_store.put_if_absent(StoredToolResult(intent.idempotency_key, intent.call_id, intent.tool, result.ok, result.value if result.ok else None, result.error, arguments))
            if not self._stored_matches_call(stored, ToolCall(intent.tool, arguments, intent.call_id, idempotency_key=intent.idempotency_key)):
                raise ToolBoundaryError("idempotency key conflicts with stored tool intent")
        if self.intent_store and not (intent.owner_id and intent.claim_token): self.intent_store.mark(intent.idempotency_key, "completed" if result.ok else "failed")
        return result
