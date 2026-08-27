from dataclasses import dataclass


@dataclass(frozen=True)
class RecoveryOutcome:
    execution_id: str
    status: str


def test_recovery_outcome_is_structured_and_stable():
    outcome = RecoveryOutcome("exec-1", "skipped_by_lease")
    assert outcome.execution_id == "exec-1"
    assert outcome.status in {"recovered", "skipped_by_lease", "failed"}
