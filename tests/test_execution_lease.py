from datetime import datetime, timedelta, timezone
import json

from runtime.execution_lease import ExecutionLeaseStore


def test_only_one_owner_can_hold_active_lease(tmp_path):
    store = ExecutionLeaseStore(str(tmp_path / "leases.json"), ttl_seconds=60)
    first = store.acquire("e1", "node-a")
    assert first is not None
    assert first.fencing_token == 1
    assert store.acquire("e1", "node-b") is None
    assert store.release("e1", "node-a", first.fencing_token) is True
    second = store.acquire("e1", "node-b")
    assert second is not None
    assert second.fencing_token == 2


def test_expired_lease_can_be_taken_over_with_new_fencing_token(tmp_path):
    path = tmp_path / "leases.json"
    store = ExecutionLeaseStore(str(path), ttl_seconds=60)
    first = store.acquire("e1", "node-a")
    raw = json.loads(path.read_text())
    raw["e1"]["expires_at"] = (datetime.now(timezone.utc) - timedelta(seconds=1)).isoformat()
    path.write_text(json.dumps(raw))
    second = store.acquire("e1", "node-b")
    assert first is not None
    assert second is not None
    assert second.fencing_token > first.fencing_token


def test_stale_fencing_token_cannot_release_new_owner(tmp_path):
    store = ExecutionLeaseStore(str(tmp_path / "leases.json"), ttl_seconds=60)
    first = store.acquire("e1", "node-a")
    store.release("e1", "node-a", first.fencing_token)
    second = store.acquire("e1", "node-b")
    assert store.release("e1", "node-a", first.fencing_token) is False
    assert store.is_owner("e1", "node-b", second.fencing_token)
