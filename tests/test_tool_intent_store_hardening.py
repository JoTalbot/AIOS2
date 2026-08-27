import json

import pytest

from runtime.tool_intent_store import ToolIntent, ToolIntentConflictError, ToolIntentStore


def test_prepare_rejects_idempotency_key_reuse(tmp_path):
    store = ToolIntentStore(tmp_path / "intents.json")
    store.prepare(ToolIntent("k", "call-1", "send", {"x": 1}, "exec-1"))
    with pytest.raises(ToolIntentConflictError):
        store.prepare(ToolIntent("k", "call-2", "send", {"x": 1}, "exec-1"))


def test_prepare_rejects_tool_or_arguments_reuse(tmp_path):
    store = ToolIntentStore(tmp_path / "intents.json")
    store.prepare(ToolIntent("k", "call-1", "send", {"x": 1}, "exec-1"))
    with pytest.raises(ToolIntentConflictError):
        store.prepare(ToolIntent("k", "call-1", "delete", {"x": 1}, "exec-1"))


def test_expired_claim_can_be_taken_over(tmp_path):
    store = ToolIntentStore(tmp_path / "intents.json", claim_ttl_seconds=1)
    store.prepare(ToolIntent("k", "call-1", "send"))
    assert store.claim("k", "a", "t1") is not None
    raw = json.loads((tmp_path / "intents.json").read_text())
    raw["k"]["claim_expires_at"] = "2000-01-01T00:00:00+00:00"
    (tmp_path / "intents.json").write_text(json.dumps(raw))
    assert store.claim("k", "b", "t2").owner_id == "b"


def test_live_claim_cannot_be_stolen(tmp_path):
    store = ToolIntentStore(tmp_path / "intents.json", claim_ttl_seconds=60)
    store.prepare(ToolIntent("k", "call-1", "send"))
    assert store.claim("k", "a", "t1") is not None
    assert store.claim("k", "b", "t2") is None
