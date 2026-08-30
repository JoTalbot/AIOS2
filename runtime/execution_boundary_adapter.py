"""Typed adapter connecting tool results to the crash-safe execution boundary."""
from .execution_boundary import ExecutionBoundary
from .tool_protocol import ToolCall, ToolResult


class ToolExecutionBoundary:
    """Persist terminal tool outcomes through one canonical fenced boundary."""

    def __init__(self, boundary: ExecutionBoundary):
        self.boundary = boundary

    def commit(self, call: ToolCall, result: ToolResult, owner_id: str, claim_token: str) -> ToolResult:
        if result.ambiguous or result.retryable:
            return result
        committed = self.boundary.commit(
            key=call.idempotency_key,
            call_id=call.call_id,
            tool=call.tool,
            arguments=call.arguments,
            owner_id=owner_id,
            claim_token=claim_token,
            ok=result.ok,
            value=result.value,
            error=result.error,
        )
        return ToolResult(
            call.call_id, call.tool, committed.ok, committed.value, committed.error,
            False, call.idempotency_key, ambiguous=not committed.committed,
        )
