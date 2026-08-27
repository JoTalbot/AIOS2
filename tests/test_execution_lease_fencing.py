from runtime.execution_lease import ExecutionLeaseStore


def test_takeover_increments_fencing_token(tmp_path):
    store = ExecutionLeaseStore(str(tmp_path / "leases.json"), ttl_seconds=60)
    first = store.acquire("e1", "node-a")
    assert first is not None
    assert first.fencing_token == 1

    store._write({"e1": {"owner_id": "node-a", "expires_at": "2000-01-01T00:00:00+00:00", "fencing_token": 1}})
    second = store.acquire("e1", "node-b")
    assert second is not None
    assert second.fencing_token == 2
    assert not store.owns_token("e1", "node-a", first.fencing_token)
    assert store.owns_token("e1", "node-b", second.fencing_token)


def test_renew_keeps_current_fencing_generation(tmp_path):
    store = ExecutionLeaseStore(str(tmp_path / "leases.json"), ttl_seconds=60)
    lease = store.acquire("e1", "node-a")
    renewed = store.renew("e1", "node-a")
    assert renewed is not None
    assert renewed.fencing_token == lease.fencing_token
