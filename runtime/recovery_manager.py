"""Startup recovery for restart-safe AIOS executions."""
from typing import Any, Optional
from .execution_store import ExecutionState, ExecutionStore
class RecoveryManager:
    def __init__(self, store: ExecutionStore): self.store = store
    def pending(self): return self.store.resumable()
    async def recover(self, loop, agent: Any, context: Optional[dict] = None):
        recovered=[]
        for state in self.pending(): recovered.append((state.execution_id, await loop.resume(state.execution_id, agent, context=context)))
        return recovered
    def mark_failed(self, state: ExecutionState, error: BaseException):
        state.status="failed"; state.error=str(error); return self.store.save(state)
