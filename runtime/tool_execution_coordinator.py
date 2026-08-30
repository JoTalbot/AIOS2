"""Cross-layer commit coordinator for tool-backed executions.

The coordinator keeps the two durable protocols ordered: a terminal tool
outcome is persisted first, then the execution lifecycle is committed. This
makes a crash between the two phases recoverable without replaying the tool.
"""
from dataclasses import dataclass
from typing import Any, Optional

from .execution_boundary import BoundaryCommit, ExecutionBoundary
from .execution_commit import ExecutionCommit, ExecutionCommitCoordinator
from .execution_store import ExecutionState
from .tool_idempotency_store import ToolIdempotencyStore
from .tool_intent_store import ToolIntentStore


@dataclass(frozen=True)
class ToolExecutionCommit:
    tool: BoundaryCommit
    execution: Optional[ExecutionCommit]


class ToolExecutionCoordinator:
    def __init__(
        self,
        intents: ToolIntentStore,
        results: ToolIdempotencyStore,
        executions: ExecutionCommitCoordinator,
    ):
        self.boundary = ExecutionBoundary(intents, results)
        self.executions = executions

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
