import pytest

from runtime.tool_idempotency_store import StoredToolResult, ToolIdempotencyStore


def test_successful_result_survives_new_store_instance(tmp_path):
    path = tmp_path / "idempotency.json"
    first = ToolIdempotencyStore(str(path))
    result = StoredToolResult("exec-1:step-1", "call-1", "charge", True, {"ok": True})
    assert first.put_if_absent(result) == result

    second = ToolIdempotencyStore(str(path))
    assert second.get(result.idempotency_key) == result


def test_put_if_absent_preserves_first_success(tmp_path):
    store = ToolIdempotencyStore(str(tmp_path / "idempotency.json"))
    first = StoredToolResult("k", "c1", "tool", True, "first")
    second = StoredToolResult("k", "c2", "tool", True, "second")
    assert store.put_if_absent(first) == first
    assert store.put_if_absent(second) == first
    assert store.get("k") == first


def test_missing_key_is_not_deduplicated(tmp_path):
    store = ToolIdempotencyStore(str(tmp_path / "idempotency.json"))
    assert store.get(None) is None
