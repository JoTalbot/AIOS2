from runtime.execution_lease import ExecutionLeaseStore


def test_only_one_owner_can_hold_active_lease(tmp_path):
    store = ExecutionLeaseStore(str(tmp_path / "leases.json"), ttl_seconds=60)
    assert store.acquire("e1", "node-a") is not None
    assert store.acquire("e1", "node-b") is None
    assert store.release("e1", "node-a") is True
    assert store.acquire("e1", "node-b") is not None


def test_expired_lease_can_be_taken_over(tmp_path):
    store = ExecutionLeaseStore(str(tmp_path / "leases.json"), ttl_seconds=-1)
    assert store.acquire("e1", "node-a") is not None
    assert store.acquire("e1", "node-b") is not None
