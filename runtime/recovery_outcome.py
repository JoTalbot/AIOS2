"""Stable, non-sensitive recovery result contract."""
from dataclasses import dataclass
from typing import Literal
RecoveryStatus = Literal["recovered", "skipped_by_lease", "failed"]
_ALLOWED_STATUSES = frozenset(("recovered", "skipped_by_lease", "failed"))
@dataclass(frozen=True)
class RecoveryOutcome:
    """Immutable recovery result with compatibility for the legacy tuple API."""
    execution_id: str
    status: RecoveryStatus
    def __post_init__(self) -> None:
        if not isinstance(self.execution_id, str) or not self.execution_id: raise ValueError("execution_id must be a non-empty string")
        if self.status not in _ALLOWED_STATUSES: raise ValueError(f"unsupported recovery status: {self.status!r}")
    def as_dict(self) -> dict[str, str]: return {"execution_id": self.execution_id, "status": self.status}
    def __eq__(self, other):
        if isinstance(other, tuple) and len(other) == 2:
            legacy_status = "resumed" if self.status == "recovered" else self.status
            return (self.execution_id, legacy_status) == other
        if isinstance(other, RecoveryOutcome): return (self.execution_id, self.status) == (other.execution_id, other.status)
        return NotImplemented
    def __hash__(self): return hash((self.execution_id, self.status))
