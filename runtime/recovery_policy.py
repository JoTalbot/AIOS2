"""Safety policy for reconciling ambiguous side-effecting tool intents."""
from dataclasses import dataclass
from typing import Any, Optional

TERMINAL_STATUSES = frozenset({"completed", "failed"})

@dataclass(frozen=True)
class RecoveryDecision:
    status: str
    reason: str
    result: Any = None

class RecoveryPolicy:
    """Allow automatic finalization only when durable terminal evidence exists."""
    def decide(self, journal_record: Optional[Any]) -> RecoveryDecision:
        if journal_record is None:
            return RecoveryDecision("ambiguous", "no_durable_evidence")
        status = getattr(journal_record, "status", None)
        if status not in TERMINAL_STATUSES:
            return RecoveryDecision("ambiguous", "terminal_evidence_missing")
        return RecoveryDecision(status, "durable_terminal_evidence", getattr(journal_record, "result", None))
