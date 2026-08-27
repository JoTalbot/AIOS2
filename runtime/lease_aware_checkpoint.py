"""Checkpoint adapter that refuses stale execution owners and propagates fencing."""

from .recovery_checkpoint import RecoveryCheckpoint

class LeaseAwareCheckpoint:
    def __init__(self, checkpoint: RecoveryCheckpoint, lease_store, owner_id: str):
        self.checkpoint, self.lease_store, self.owner_id = checkpoint, lease_store, owner_id
        self._fences = {}

    def _assert_owner(self, execution_id: str, *, acquire=False):
        token = self._fences.get(execution_id)
        if token is None and self.lease_store.is_owner(execution_id, self.owner_id):
            token = self.lease_store.fencing_token(execution_id)
            self._fences[execution_id] = token
        if acquire and token is None:
            lease = self.lease_store.acquire(execution_id, self.owner_id)
            if lease is not None:
                token = lease.fencing_token
                self._fences[execution_id] = token
        if token is not None and self.lease_store.owns_token(execution_id, self.owner_id, token):
            return token
        raise RuntimeError(f"execution '{execution_id}' lease is not owned by '{self.owner_id}'")

    def _fence(self, state, *, acquire=False):
        token = self._assert_owner(state.execution_id, acquire=acquire)
        state.fencing_token = token
        return token

    def mark_running(self, state, attempt, plan=None):
        self._fence(state, acquire=state.status == "pending")
        return self.checkpoint.mark_running(state, attempt, plan)

    def mark_completed(self, state, result=None):
        self._fence(state)
        return self.checkpoint.mark_completed(state, result)

    def mark_failed(self, state, error):
        self._fence(state)
        return self.checkpoint.mark_failed(state, error)

    def transition(self, state, status, **updates):
        self._fence(state)
        return self.checkpoint.transition(state, status, **updates)
