import pytest

from runtime.tool_intent_store import ToolIntent, ToolIntentStore


def test_mark_does_not_allow_claim_takeover(tmp_path):
    store = ToolIntentStore(str(tmp_path / "intents.json"), claim_ttl_seconds=60)
    store.prepare(ToolIntent("k", "c", "tool"))
    claimed = store.claim("k", "owner-a", "token-a")
    assert claimed is not None

    # Direct state mutation must not be able to bypass an active claim.
    # The public owner-bound transition API remains the authority for claimed work.
    with pytest.raises(TypeError):
        store.mark("k", "completed", "owner-b", "token-b")

    current = store.get("k")
    assert current is not None
    assert current.state == "executing"
    assert current.owner_id == "owner-a"
    assert current.claim_token == "token-a"


def test_stale_owner_cannot_complete_after_claim_expiry(tmp_path):
    store = ToolIntentStore(str(tmp_path / "intents.json"), claim_ttl_seconds=1)
    store.prepare(ToolIntent("k", "c", "tool"))
    claimed = store.claim("k", "owner-a", "token-a")
    assert claimed is not None

    assert store.mark_claimed("k", "owner-a", "wrong-token", "completed") is None
    current = store.get("k")
    assert current is not None
    assert current.state == "executing"
