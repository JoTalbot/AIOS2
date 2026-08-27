"""Pytest configuration for the runtime test suite."""
import pytest

CHAOS_TEST_PREFIXES = (
    "test_end_to_end_fencing_multiprocess.py",
    "test_sigkill_recovery_boundaries.py",
    "test_external_side_effect_sigkill.py",
    "test_idempotency_multiprocess.py",
    "test_external_side_effect_race.py",
    "test_full_execution_fencing_chaos.py",
    "test_real_executor_idempotency_sigkill.py",
    "test_tool_executor_sigkill_boundary.py",
    "test_tool_executor_multiprocess_chaos.py",
)

E2E_HINTS = ("e2e", "end_to_end", "full_autonomy")
RUNTIME_HINTS = ("execution", "executor", "autonomous_loop", "loop_state", "recovery", "fencing", "ledger", "intent")
INTEGRATION_HINTS = ("api", "auth", "config", "server", "http", "integration")


def pytest_collection_modifyitems(config, items):
    chaos = pytest.mark.chaos
    for item in items:
        name = item.path.name.lower()
        if name in CHAOS_TEST_PREFIXES:
            item.add_marker(chaos)
            continue
        if any(hint in name for hint in E2E_HINTS):
            item.add_marker(pytest.mark.e2e)
        elif any(hint in name for hint in RUNTIME_HINTS):
            item.add_marker(pytest.mark.runtime)
        elif any(hint in name for hint in INTEGRATION_HINTS):
            item.add_marker(pytest.mark.integration)
        else:
            item.add_marker(pytest.mark.unit)
