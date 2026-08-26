"""Execution checkpoint adapter using the canonical commit boundary."""

from .execution_store import ExecutionState, ExecutionStore


class RecoveryCheckpoint:
    def __init__(self, store: ExecutionStore, committer=None):
        self.store = store
        self.committer = committer

    def mark_running(self, state: ExecutionState, attempt: int, plan=None):
        if self.committer:
            updates = {"attempt": attempt}
            if plan is not None:
                updates["plan"] = plan
            return self.committer.commit(state, "running", updates=updates)
        state.status = "running"
        state.attempt = attempt
        if plan is not None:
            state.plan = plan
        return self.store.save(state)

    def mark_completed(self, state: ExecutionState, result=None):
        if self.committer:
            return self.committer.commit(state, "completed", checkpoint=result, updates={"error": None})
        state.status = "completed"
        state.result = result
        state.error = None
        return self.store.save(state)

    def mark_failed(self, state: ExecutionState, error):
        if self.committer:
            return self.committer.commit(state, "failed", reason=str(error), updates={"error": str(error)})
        state.status = "failed"
        state.error = str(error)
        return self.store.save(state)

    def transition(self, state: ExecutionState, status: str, **updates):
        if self.committer:
            return self.committer.commit(state, status, reason=updates.pop("reason", None), updates=updates)
        return self.store.transition(state.execution_id, status, **updates)
