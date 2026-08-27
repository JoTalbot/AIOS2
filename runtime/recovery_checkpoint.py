"""Checkpoint adapter using the canonical execution commit boundary."""

from .execution_store import ExecutionState, ExecutionStore
from .execution_audit import ExecutionAuditLog
from .execution_commit import ExecutionCommitCoordinator


class RecoveryCheckpoint:
    """Recovery checkpoint that always delegates lifecycle mutation to the canonical coordinator."""

    def __init__(self, store: ExecutionStore, committer=None):
        self.store = store
        if committer is None:
            audit = getattr(store, "audit_log", None) or ExecutionAuditLog()
            committer = ExecutionCommitCoordinator(store, audit)
        self.committer = committer

    def mark_running(self, state: ExecutionState, attempt: int, plan=None):
        updates = {"attempt": attempt}
        if plan is not None:
            updates["plan"] = plan
        return self.committer.commit(state, "running", updates=updates, fencing_token=state.fencing_token)

    def mark_completed(self, state: ExecutionState, result=None):
        return self.committer.commit(state, "completed", checkpoint=result, updates={"error": None}, fencing_token=state.fencing_token)

    def mark_failed(self, state: ExecutionState, error):
        return self.committer.commit(state, "failed", reason=str(error), updates={"error": str(error)}, fencing_token=state.fencing_token)

    def transition(self, state: ExecutionState, status: str, **updates):
        reason = updates.pop("reason", None)
        return self.committer.commit(state, status, reason=reason, updates=updates, fencing_token=state.fencing_token)
