"""Stable, non-sensitive recovery result contract."""
from dataclasses import dataclass
from typing import Literal

RecoveryStatus = Literal["recovered", "skipped_by_lease", "failed"]


@dataclass(frozen=True)
class RecoveryOutcome:
    execution_id: str
    status: RecoveryStatus

    def as_dict(self) -> dict[str, str]:
        return {"execution_id": self.execution_id, "status": self.status}
