import pytest

from runtime.tool_idempotency_store import StoredToolResult, ToolIdempotencyStore


def test_failure_result_is_durable_and_replayed_without_execution(tmp_path):
    path = str(tmp_path / "results.json")
    store = ToolIdempotencyStore(path)
    stored = store.put_if_absent(
        StoredToolResult("k", "call-1", "remote_write", False, None, "remote failure")
    )

    reopened = ToolIdempotencyStore(path)
    recovered = reopened.get("k")

    assert stored.ok is False
    assert recovered is not None
    assert recovered.ok is False
    assert recovered.error == "remote failure"


def test_duplicate_failure_does_not_replace_first_durable_outcome(tmp_path):
    store = ToolIdempotencyStore(str(tmp_path / "results.json"))
    first = store.put_if_absent(
        StoredToolResult("k", "call-1", "remote_write", False, None, "first failure")
    )
    second = store.put_if_absent(
        StoredToolResult("k", "call-2", "remote_write", False, None, "second failure")
    )

    assert first.error == "first failure"
    assert second.error == "first failure"
