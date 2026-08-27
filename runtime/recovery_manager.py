"""Startup recovery for restart-safe AIOS executions."""

from typing import Any, Optional

from .execution_audit import ExecutionAuditLog
from .execution_commit import ExecutionCommitCoordinator
from .execution_store import ExecutionStore


class RecoveryManager:
    def __init__(self, store: ExecutionStore, commit_coordinator=None):
        self.store = store
        self.commit_coordinator = commit_coordinator or ExecutionCommitCoordinator(
            store, ExecutionAuditLog()
        )

    def pending(self):
        return self.store.resumable()

    async def recover(self, loop, agent: Any, context: Optional[dict] = None):
        recovered = []
        for state in self.pending():
            if hasattr(loop, "resume"):
                result = await loop.resume(state.execution_id, agent, context=context)
            else:
                result = await loop.run(
                    state.goal or "",
                    agent,
                    context=context,
                    execution_context=getattr(state, "execution_context", None),
                )
            recovered.append((state.execution_id, result))
        return recovered

    def mark_failed(self, state, error: BaseException):
        """Persist recovery failure through the canonical lifecycle boundary."""
        return self.commit_coordinator.commit(
            state,
            "failed",
            reason=str(error),
            updates={"error": str(error)},
        )
