from runtime.execution_lease import ExecutionLeaseStore


def test_owner_can_renew_active_lease(tmp_path):
    store = ExecutionLeaseStore(str(tmp_path / "leases.json"), ttl_seconds=60)
    first = store.acquire("e1", "node-a")
    renewed = store.renew("e1", "node-a")
    assert first is not None
    assert renewed is not None
    assert renewed.owner_id == "node-a"
    assert store.is_owner("e1", "node-a")


def test_non_owner_cannot_renew_lease(tmp_path):
    store = ExecutionLeaseStore(str(tmp_path / "leases.json"), ttl_seconds=60)
    store.acquire("e1", "node-a")
    assert store.renew("e1", "node-b") is None
    assert store.is_owner("e1", "node-a")


def test_stale_fencing_token_cannot_renew_reacquired_same_owner(tmp_path):
    store = ExecutionLeaseStore(str(tmp_path / "leases.json"), ttl_seconds=60)
    first = store.acquire("e1", "node-a")
    assert first is not None
    assert store.release("e1", "node-a", first.fencing_token)

    second = store.acquire("e1", "node-a")
    assert second is not None
    assert second.fencing_token > first.fencing_token
    assert store.renew("e1", "node-a", first.fencing_token) is None
    assert store.is_owner("e1", "node-a", second.fencing_token)
