from dataclasses import dataclass

import pytest

from runtime.recovery_outcome import RecoveryOutcome


@dataclass(frozen=True)
class LegacyRecoveryOutcome:
    execution_id: str
    status: str


def test_recovery_outcome_is_structured_and_stable():
    outcome = RecoveryOutcome("exec-1", "skipped_by_lease")
    assert outcome.execution_id == "exec-1"
    assert outcome.status == "skipped_by_lease"


def test_recovery_outcome_rejects_empty_execution_id():
    with pytest.raises(ValueError, match="execution_id"):
        RecoveryOutcome("", "recovered")


def test_recovery_outcome_rejects_unknown_status():
    with pytest.raises(ValueError, match="unsupported recovery status"):
        RecoveryOutcome("exec-1", "unknown")


def test_recovery_outcome_serializes_only_stable_public_fields():
    outcome = RecoveryOutcome("exec-1", "failed")
    assert outcome.as_dict() == {"execution_id": "exec-1", "status": "failed"}
