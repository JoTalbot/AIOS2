"""Checkpoint adapter using the canonical execution commit boundary."""

from .recovery_checkpoint import RecoveryCheckpoint as _RecoveryCheckpoint


class RecoveryCheckpoint(_RecoveryCheckpoint):
    """Compatibility facade that requires a canonical committer."""

    def __init__(self, store, committer=None):
        if committer is None:
            raise ValueError("RecoveryCheckpoint requires the canonical ExecutionCommitCoordinator")
        super().__init__(store, committer=committer)
