from datetime import datetime, timedelta, timezone

from runtime.tool_intent_store import ToolIntent, ToolIntentStore


def test_expired_claim_cannot_mark_terminal_after_reclaim(tmp_path):
    store = ToolIntentStore(str(tmp_path / "intents.json"), claim_ttl_seconds=1)
    store.prepare(ToolIntent("k", "c", "write", {}))
    first = store.claim("k", "worker-a", "token-a")
    assert first is not None
    data = store._read()
    data["k"]["claim_expires_at"] = (datetime.now(timezone.utc) - timedelta(seconds=1)).isoformat()
    store._write(data)
    second = store.claim("k", "worker-b", "token-b")
    assert second is not None
    assert store.mark_claimed("k", "worker-a", "token-a", "completed") is None
    assert store.mark_claimed("k", "worker-b", "token-b", "completed") is not None
