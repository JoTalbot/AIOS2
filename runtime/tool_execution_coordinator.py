"""Coordinate durable tool commits with execution-state transitions."""
from typing import Any

from .execution_boundary import ExecutionBoundary, BoundaryCommit
from .execution_state import ExecutionState


class ToolExecutionCommit:
    def __init__(self, tool_commit: BoundaryCommit, execution_commit):
        self.tool_commit = tool_commit
        self.execution_commit = execution_commit


class ToolExecutionCoordinator:
    def __init__(self, executions, boundary: ExecutionBoundary):
        self.executions = executions
        self.boundary = boundary

    def commit(
        self,
        state: ExecutionState,
        *,
        key: str,
        call_id: str,
        tool: str,
        owner_id: str,
        claim_token: str,
        ok: bool,
        value: Any = None,
        error: str | None = None,
        execution_status: str | None = None,
        arguments: dict[str, Any] | None = None,
    ) -> ToolExecutionCommit:
        """Durably commit a tool result, then its execution state.

        A failed/fenced execution-layer commit never causes the already durable
        tool outcome to be executed again. Callers can reconcile the execution
        journal independently. ``arguments`` remains optional for compatibility
        with older coordinator callers; newer callers should pass the tool args.
        """
        tool_commit = self.boundary.commit(
            key=key,
            call_id=call_id,
            tool=tool,
            arguments=arguments,
            owner_id=owner_id,
            claim_token=claim_token,
            ok=ok,
            value=value,
            error=error,
        )
        if not tool_commit.committed:
            return ToolExecutionCommit(tool_commit, None)

        target = execution_status or ("completed" if ok else "failed")
        execution_commit = self.executions.commit(
            state,
            target,
            checkpoint=tool_commit.value if ok else None,
            reason=tool_commit.error if not ok else None,
        )
        return ToolExecutionCommit(tool_commit, execution_commit)
