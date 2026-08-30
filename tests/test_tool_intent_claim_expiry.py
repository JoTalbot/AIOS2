from datetime import datetime, timedelta, timezone
import json

from runtime.tool_intent_store import ToolIntent, ToolIntentStore


def test_expired_claim_can_be_reclaimed(tmp_path):
    path = tmp_path / "intents.json"
    store = ToolIntentStore(str(path), claim_ttl_seconds=60)
    store.prepare(ToolIntent("k", "c", "write", {}))
    first = store.claim("k", "worker-a", "token-a")
    data = json.loads(path.read_text())
    data["k"]["claim_expires_at"] = (datetime.now(timezone.utc) - timedelta(seconds=1)).isoformat()
    path.write_text(json.dumps(data))
    second = store.claim("k", "worker-b", "token-b")
    assert second is not None
    assert second.owner_id == "worker-b"
    assert second.claim_token == "token-b"


def test_live_claim_cannot_be_stolen(tmp_path):
    store = ToolIntentStore(str(tmp_path / "intents.json"), claim_ttl_seconds=60)
    store.prepare(ToolIntent("k", "c", "write", {}))
    assert store.claim("k", "worker-a", "token-a") is not None
    assert store.claim("k", "worker-b", "token-b") is None
