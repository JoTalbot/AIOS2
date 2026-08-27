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


def pytest_collection_modifyitems(config, items):
    marker = pytest.mark.chaos
    for item in items:
        if item.path.name in CHAOS_TEST_PREFIXES:
            item.add_marker(marker)
