"""Checkpoint adapter that refuses stale execution owners."""

from .recovery_checkpoint import RecoveryCheckpoint


class LeaseAwareCheckpoint:
    def __init__(self, checkpoint: RecoveryCheckpoint, lease_store, owner_id: str):
        self.checkpoint = checkpoint
        self.lease_store = lease_store
        self.owner_id = owner_id

    def _assert_owner(self, execution_id: str, fencing_token=None):
        if not execution_id:
            raise ValueError("execution_id is required for lease-aware checkpointing")
        if fencing_token is None:
            raise ValueError("fencing_token is required for lease-aware checkpointing")
        if not self.lease_store.is_owner(execution_id, self.owner_id, fencing_token):
            raise RuntimeError(f"execution '{execution_id}' lease is not owned by '{self.owner_id}'")

    def mark_running(self, state, attempt, plan=None, *, fencing_token=None):
        self._assert_owner(state.execution_id, fencing_token)
        return self.checkpoint.mark_running(state, attempt, plan)

    def mark_completed(self, state, result=None, *, fencing_token=None):
        self._assert_owner(state.execution_id, fencing_token)
        return self.checkpoint.mark_completed(state, result)

    def mark_failed(self, state, error, *, fencing_token=None):
        self._assert_owner(state.execution_id, fencing_token)
        return self.checkpoint.mark_failed(state, error)
