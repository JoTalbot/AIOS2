"""Checkpoint helpers with optimistic version and fencing enforcement."""

from .execution_store import ExecutionState, ExecutionStore, ExecutionVersionConflictError


class RecoveryCheckpoint:
    def __init__(self, store: ExecutionStore):
        self.store = store

    def mark_running(self, state: ExecutionState, attempt: int, plan=None):
        if attempt < 1:
            raise ValueError("checkpoint attempt must be >= 1")
        state.status = "running"
        state.attempt = attempt
        if plan is not None:
            state.plan = plan
        return self._cas(state)

    def mark_completed(self, state: ExecutionState, result=None):
        state.status = "completed"
        state.result = result
        state.error = None
        return self._cas(state)

    def mark_failed(self, state: ExecutionState, error):
        if error is None:
            raise ValueError("checkpoint failure requires an error")
        state.status = "failed"
        state.error = str(error)
        return self._cas(state)

    def _cas(self, state: ExecutionState):
        return self.store.compare_and_set(state, expected_version=state.version)
