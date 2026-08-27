"""Stable, non-sensitive recovery result contract."""
from dataclasses import dataclass
from typing import Literal

RecoveryStatus = Literal["recovered", "skipped_by_lease", "failed"]
_ALLOWED_STATUSES = frozenset(("recovered", "skipped_by_lease", "failed"))


@dataclass(frozen=True)
class RecoveryOutcome:
    """Immutable recovery result safe to expose to operators and APIs."""

    execution_id: str
    status: RecoveryStatus

    def __post_init__(self) -> None:
        if not isinstance(self.execution_id, str) or not self.execution_id:
            raise ValueError("execution_id must be a non-empty string")
        if self.status not in _ALLOWED_STATUSES:
            raise ValueError(f"unsupported recovery status: {self.status!r}")

    def as_dict(self) -> dict[str, str]:
        """Return the stable wire representation without internal error data."""
        return {"execution_id": self.execution_id, "status": self.status}
