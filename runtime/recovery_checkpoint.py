"""Checkpoint helpers with optimistic version and fencing enforcement."""
from .execution_store import ExecutionState, ExecutionStore
class RecoveryCheckpoint:
    def __init__(self, store): self.store=store
    def mark_running(self, state, attempt, plan=None):
        attempt=max(1, int(attempt)); state.status="running"; state.attempt=attempt
        if plan is not None: state.plan=plan
        return self.store.compare_and_set(state, expected_version=state.version)
    def mark_completed(self,state,result=None):
        state.status="completed"; state.result=result; state.error=None; return self.store.compare_and_set(state, expected_version=state.version)
    def mark_failed(self,state,error):
        if error is None: raise ValueError("checkpoint failure requires an error")
        state.status="failed"; state.error=str(error); return self.store.compare_and_set(state, expected_version=state.version)
