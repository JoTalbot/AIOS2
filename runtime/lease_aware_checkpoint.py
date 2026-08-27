"""Checkpoint adapter that refuses stale execution owners."""

from .recovery_checkpoint import RecoveryCheckpoint


class LeaseAwareCheckpoint:
    def __init__(self, checkpoint: RecoveryCheckpoint, lease_store, owner_id: str):
        self.checkpoint = checkpoint
        self.lease_store = lease_store
        self.owner_id = owner_id

    def _assert_owner(self, execution_id: str, fencing_token=None, *, legacy_unpersisted=False):
        if not execution_id:
            raise ValueError("execution_id is required for lease-aware checkpointing")
        if fencing_token is None:
            # Legacy callers that have not persisted the state yet can still use
            # owner validation. Once a durable version exists, an explicit token
            # is mandatory so the write cannot race a newer lease generation.
            if not legacy_unpersisted:
                raise ValueError("fencing_token is required for lease-aware checkpointing")
            current = self.lease_store._read().get(execution_id)
            fencing_token = current.get("fencing_token") if current and current.get("owner_id") == self.owner_id else None
        if fencing_token is None or not self.lease_store.is_owner(execution_id, self.owner_id, fencing_token):
            raise RuntimeError(f"execution '{execution_id}' lease is not owned by '{self.owner_id}'")
        return fencing_token

    def _check(self, state, fencing_token):
        return self._assert_owner(state.execution_id, fencing_token, legacy_unpersisted=getattr(state, "version", 0) == 0)

    def mark_running(self, state, attempt, plan=None, *, fencing_token=None):
        self._check(state, fencing_token)
        return self.checkpoint.mark_running(state, attempt, plan)

    def mark_completed(self, state, result=None, *, fencing_token=None):
        self._check(state, fencing_token)
        return self.checkpoint.mark_completed(state, result)

    def mark_failed(self, state, error, *, fencing_token=None):
        self._check(state, fencing_token)
        return self.checkpoint.mark_failed(state, error)
