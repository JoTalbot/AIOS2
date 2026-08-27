"""Top-level crash recovery orchestration.

Recovery is deliberately ordered: reconcile durable execution commits first,
then resume only executions that remain resumable. This prevents a process
restart from replaying work whose terminal commit was already persisted.
"""
from dataclasses import dataclass
from typing import Any, Optional

from .recovery_outcome import RecoveryOutcome


@dataclass(frozen=True)
class RecoveryReport:
    reconciled_commit_ids: tuple[str, ...]
    outcomes: tuple[RecoveryOutcome, ...]

    @property
    def recovered(self) -> int:
        return sum(item.status == "recovered" for item in self.outcomes)

    @property
    def skipped(self) -> int:
        return sum(item.status == "skipped_by_lease" for item in self.outcomes)

    @property
    def failed(self) -> int:
        return sum(item.status == "failed" for item in self.outcomes)

    @property
    def stale(self) -> int:
        return sum(item.status == "stale" for item in self.outcomes)


class RecoveryOrchestrator:
    """Coordinate commit reconciliation and execution resumption."""

    def __init__(self, manager, commit_coordinator=None):
        self.manager = manager
        self.commit_coordinator = commit_coordinator

    def reconcile_commits(self) -> list[str]:
        if self.commit_coordinator is None:
            return []
        return list(self.commit_coordinator.reconcile())

    async def recover(
        self,
        loop: Any,
        agent: Any,
        context: Optional[dict] = None,
        *,
        continue_on_error: bool = True,
    ) -> RecoveryReport:
        # Durable commit reconciliation must happen before manager.pending().
        reconciled = self.reconcile_commits()
        outcomes = await self.manager.recover(
            loop,
            agent,
            context=context,
            continue_on_error=continue_on_error,
        )
        return RecoveryReport(tuple(reconciled), tuple(outcomes))
