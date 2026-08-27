from datetime import datetime, timedelta, timezone

from runtime.tool_intent_store import ToolIntent, ToolIntentStore


def test_intent_survives_restart(tmp_path):
    path = tmp_path / "intents.json"
    store = ToolIntentStore(str(path))
    intent = ToolIntent("exec:step:1", "call-1", "send_email", {"to": "x@example.test"}, "exec")
    store.prepare(intent)
    restarted = ToolIntentStore(str(path))
    assert restarted.get(intent.idempotency_key).state == "prepared"


def test_intent_is_idempotent_and_recoverable(tmp_path):
    store = ToolIntentStore(str(tmp_path / "intents.json"))
    intent = ToolIntent("k", "c", "write", {})
    assert store.prepare(intent) == intent
    assert store.prepare(intent) == intent
    claimed = store.claim("k", "owner-a", "token-a")
    assert claimed is not None
    assert claimed.state == "executing"
    assert store.pending()[0].idempotency_key == "k"
    assert store.mark_claimed("k", "owner-a", "token-a", "completed") is not None
    assert store.pending() == []


def test_terminal_transition_requires_authorized_claim(tmp_path):
    store = ToolIntentStore(str(tmp_path / "intents.json"))
    store.prepare(ToolIntent("k", "c", "write", {}))
    assert store.mark("k", "completed") is None
    assert store.get("k").state == "prepared"
    claimed = store.claim("k", "owner-a", "token-a")
    assert claimed is not None
    assert store.mark("k", "completed") is None
    assert store.mark_claimed("k", "owner-a", "wrong-token", "completed") is None
    assert store.get("k").state == "executing"
    assert store.mark_claimed("k", "owner-a", "token-a", "completed") is not None
    assert store.get("k").state == "completed"


def test_stale_claim_can_be_reclaimed_by_new_owner(tmp_path):
    store = ToolIntentStore(str(tmp_path / "intents.json"), claim_ttl_seconds=60)
    store.prepare(ToolIntent("k", "c", "write", {}))
    first = store.claim("k", "owner-a", "token-a")
    assert first is not None
    path = store.path
    raw = __import__("json").loads(path.read_text())
    raw["k"]["claim_expires_at"] = (datetime.now(timezone.utc) - timedelta(seconds=1)).isoformat()
    path.write_text(__import__("json").dumps(raw))
    reclaimed = store.claim("k", "owner-b", "token-b")
    assert reclaimed is not None
    assert reclaimed.owner_id == "owner-b"
    assert reclaimed.claim_token == "token-b"
    assert store.mark_claimed("k", "owner-a", "token-a", "completed") is None
    assert store.get("k").state == "executing"


def test_live_claim_cannot_be_stolen(tmp_path):
    store = ToolIntentStore(str(tmp_path / "intents.json"), claim_ttl_seconds=60)
    store.prepare(ToolIntent("k", "c", "write", {}))
    assert store.claim("k", "owner-a", "token-a") is not None
    assert store.claim("k", "owner-b", "token-b") is None
    assert store.get("k").owner_id == "owner-a"


def test_expired_owner_cannot_finish_after_reclaim(tmp_path):
    store = ToolIntentStore(str(tmp_path / "intents.json"), claim_ttl_seconds=1)
    store.prepare(ToolIntent("k", "c", "write", {}))
    assert store.claim("k", "owner-a", "token-a") is not None
    raw = __import__("json").loads(store.path.read_text())
    raw["k"]["claim_expires_at"] = (datetime.now(timezone.utc) - timedelta(seconds=1)).isoformat()
    store.path.write_text(__import__("json").dumps(raw))
    assert store.claim("k", "owner-b", "token-b") is not None
    assert store.mark_claimed("k", "owner-a", "token-a", "completed") is None
    assert store.get("k").owner_id == "owner-b"
