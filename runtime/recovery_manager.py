"""Startup recovery for restart-safe AIOS executions."""

from typing import Any, Optional

from .execution_store import ExecutionState, ExecutionStore


class RecoveryManager:
    """Resume recoverable executions while isolating individual failures."""

    def __init__(self, store: ExecutionStore, lease_store=None, owner_id: Optional[str] = None):
        if (lease_store is None) != (owner_id is None):
            raise ValueError("lease_store and owner_id must be provided together")
        self.store = store
        self.lease_store = lease_store
        self.owner_id = owner_id

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
        """Resume pending executions, acquiring a lease before each resume."""
        recovered = []
        for state in self.pending():
            lease = None
            if self.lease_store is not None:
                lease = self.lease_store.acquire(state.execution_id, self.owner_id)
                if lease is None:
                    continue
            try:
                result = await loop.resume(state.execution_id, agent, context=context)
            except Exception as exc:
                self.mark_failed(state, exc)
                if not continue_on_error:
                    raise
                continue
            finally:
                if lease is not None:
                    self.lease_store.release(state.execution_id, self.owner_id)
            recovered.append((state.execution_id, result))
        return recovered

    def mark_failed(self, state: ExecutionState, error: BaseException):
        state.status = "failed"
        state.error = str(error)
        return self.store.save(state)
