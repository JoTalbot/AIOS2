"""Policy decisions for crash recovery of AIOS executions."""

from dataclasses import dataclass
from enum import Enum
from typing import Any, Optional


class RecoveryAction(str, Enum):
    RETRY = "retry"
    SKIP = "skip"
    QUARANTINE = "quarantine"
    MANUAL_REVIEW = "manual_review"


@dataclass(frozen=True)
class RecoveryDecision:
    execution_id: str
    action: RecoveryAction
    reason: str
    attempt: int


@dataclass(frozen=True)
class EvidenceDecision:
    status: str
    reason: str
    result: Any = None


class RecoveryPolicy:
    """Deterministic recovery policy, safe to evaluate repeatedly."""

    def __init__(self, max_attempts: int = 3):
        self.max_attempts = max_attempts

    def decide(self, execution_id: str, status: str, attempt: int, *, journal_corrupt: bool = False, reason: Optional[str] = None) -> RecoveryDecision:
        if journal_corrupt:
            return RecoveryDecision(execution_id, RecoveryAction.QUARANTINE, reason or "corrupt commit journal", attempt)
        if status not in {"running", "retrying"}:
            return RecoveryDecision(execution_id, RecoveryAction.SKIP, reason or f"state {status} is not resumable", attempt)
        if attempt >= self.max_attempts:
            return RecoveryDecision(execution_id, RecoveryAction.MANUAL_REVIEW, reason or "maximum recovery attempts reached", attempt)
        return RecoveryDecision(execution_id, RecoveryAction.RETRY, reason or "resumable execution", attempt)

    def decide_evidence(self, journal_record: Optional[Any]) -> EvidenceDecision:
        """Finalize only from durable terminal evidence; otherwise remain ambiguous."""
        if journal_record is None:
            return EvidenceDecision("ambiguous", "no_durable_evidence")
        status = getattr(journal_record, "status", None)
        if status not in {"completed", "failed"}:
            return EvidenceDecision("ambiguous", "terminal_evidence_missing")
        return EvidenceDecision(status, "durable_terminal_evidence", getattr(journal_record, "result", None))
