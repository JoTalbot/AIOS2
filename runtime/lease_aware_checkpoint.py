"""Checkpoint adapter that refuses stale execution owners."""

from .recovery_checkpoint import RecoveryCheckpoint


class LeaseAwareCheckpoint:
    def __init__(self, checkpoint: RecoveryCheckpoint, lease_store, owner_id: str):
        self.checkpoint, self.lease_store, self.owner_id = checkpoint, lease_store, owner_id

    def _assert_owner(self, execution_id: str, *, acquire=False):
        if self.lease_store.is_owner(execution_id, self.owner_id):
            return
        if acquire and self.lease_store.acquire(execution_id, self.owner_id) is not None:
            return
        raise RuntimeError(f"execution '{execution_id}' lease is not owned by '{self.owner_id}'")

    def mark_running(self, state, attempt, plan=None):
        self._assert_owner(state.execution_id, acquire=state.status == "pending")
        return self.checkpoint.mark_running(state, attempt, plan)

    def mark_completed(self, state, result=None):
        self._assert_owner(state.execution_id)
        return self.checkpoint.mark_completed(state, result)

    def mark_failed(self, state, error):
        self._assert_owner(state.execution_id)
        return self.checkpoint.mark_failed(state, error)

    def transition(self, state, status, **updates):
        self._assert_owner(state.execution_id)
        return self.checkpoint.transition(state, status, **updates)
