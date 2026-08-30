from runtime.recovery_policy import RecoveryAction, RecoveryPolicy


def test_evidence_policy_is_safe_to_repeat():
    policy = RecoveryPolicy()
    assert policy.decide_evidence(None).status == "ambiguous"
    assert policy.decide_evidence(None).reason == "no_durable_evidence"
    assert policy.decide_evidence(None) == policy.decide_evidence(None)


def test_worker_policy_preserves_existing_retry_contract():
    policy = RecoveryPolicy(max_attempts=2)
    assert policy.decide("e1", "running", 0).action is RecoveryAction.RETRY
    assert policy.decide("e1", "running", 2).action is RecoveryAction.MANUAL_REVIEW
