import pytest

from runtime.tool_intent_store import ToolIntent, ToolIntentStore


def test_claim_epoch_increments_on_takeover(tmp_path):
    store = ToolIntentStore(tmp_path / "intent.json", claim_ttl_seconds=1)
    store.prepare(ToolIntent("k", "c", "tool", {}))
    first = store.claim("k", "owner-a", "token-a")
    assert first.claim_epoch == 1
    assert store.release_claim("k", "owner-a", "token-a")
    second = store.claim("k", "owner-b", "token-b")
    assert second.claim_epoch == 2


def test_stale_epoch_cannot_finalize_new_claim(tmp_path):
    store = ToolIntentStore(tmp_path / "intent.json", claim_ttl_seconds=1)
    store.prepare(ToolIntent("k", "c", "tool", {}))
    first = store.claim("k", "owner-a", "token-a")
    assert store.release_claim("k", "owner-a", "token-a")
    second = store.claim("k", "owner-b", "token-b")
    assert second.claim_epoch > first.claim_epoch
    assert store.mark_claimed("k", "owner-a", "token-a", "completed", claim_epoch=first.claim_epoch) is None
    assert store.mark_claimed("k", "owner-b", "token-b", "completed", claim_epoch=second.claim_epoch) is not None
