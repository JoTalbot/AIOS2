"""Startup recovery for restart-safe AIOS executions."""

from typing import Any, Optional

from .execution_store import ExecutionState, ExecutionStore


class RecoveryManager:
    """Resume recoverable executions while isolating individual failures."""

    def __init__(self, store: ExecutionStore):
        self.store = store

    def pending(self):
        return self.store.resumable()

    async def recover(
        self,
        loop,
        agent: Any,
        context: Optional[dict] = None,
        *,
        continue_on_error: bool = True,
    ):
        """Resume pending executions without losing the rest of the recovery batch.

        When ``continue_on_error`` is false, the first resume failure is re-raised
        after its execution is durably marked failed.
        """
        recovered = []
        for state in self.pending():
            try:
                result = await loop.resume(state.execution_id, agent, context=context)
            except BaseException as exc:
                self.mark_failed(state, exc)
                if not continue_on_error:
                    raise
                continue
            recovered.append((state.execution_id, result))
        return recovered

    def mark_failed(self, state: ExecutionState, error: BaseException):
        state.status = "failed"
        state.error = str(error)
        return self.store.save(state)
