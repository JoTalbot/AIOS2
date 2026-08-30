from reliability.scenarios import FailureScenario
from reliability.validation import validate_recovery


def test_failure_scenario_lifecycle():
    scenario = FailureScenario("runtime_crash")
    assert scenario.triggered is False
    scenario.inject()
    assert scenario.triggered is True
    scenario.reset()
    assert scenario.triggered is False


def test_recovery_validation():
    assert validate_recovery({"status": "recovered"}) is True
    assert validate_recovery({"status": "broken"}) is False
