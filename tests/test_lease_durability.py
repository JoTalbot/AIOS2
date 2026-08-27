import json
import os
import time

from runtime.execution_lease import ExecutionLeaseStore


def test_lease_store_fsyncs_parent_directory_after_atomic_replace(tmp_path, monkeypatch):
    store = ExecutionLeaseStore(str(tmp_path / "leases.json"), ttl_seconds=60)
    calls = []
    real_fsync = os.fsync

    def recording_fsync(fd):
        calls.append(fd)
        return real_fsync(fd)

    monkeypatch.setattr("runtime.execution_lease.os.fsync", recording_fsync)
    lease = store.acquire("e1", "node-a")

    assert lease is not None
    assert len(calls) >= 2


def test_lease_state_survives_reload_after_acquire(tmp_path):
    path = tmp_path / "leases.json"
    first = ExecutionLeaseStore(str(path), ttl_seconds=60)
    lease = first.acquire("e1", "node-a")

    second = ExecutionLeaseStore(str(path), ttl_seconds=60)
    assert lease is not None
    assert second.is_owner("e1", "node-a", lease.fencing_token)


def test_lease_json_remains_valid_after_atomic_write(tmp_path):
    path = tmp_path / "leases.json"
    store = ExecutionLeaseStore(str(path), ttl_seconds=60)
    lease = store.acquire("e1", "node-a")

    raw = json.loads(path.read_text(encoding="utf-8"))
    assert raw["e1"]["owner_id"] == "node-a"
    assert raw["e1"]["fencing_token"] == lease.fencing_token


def test_expired_lease_can_be_taken_over_with_new_fencing_token(tmp_path):
    store = ExecutionLeaseStore(str(tmp_path / "leases.json"), ttl_seconds=1)
    first = store.acquire("e1", "node-a")
    assert first is not None
    time.sleep(1.05)

    second = store.acquire("e1", "node-b")

    assert second is not None
    assert second.owner_id == "node-b"
    assert second.fencing_token == first.fencing_token + 1
    assert not store.is_owner("e1", "node-a", first.fencing_token)
    assert store.is_owner("e1", "node-b", second.fencing_token)


def test_stale_owner_cannot_release_after_takeover(tmp_path):
    store = ExecutionLeaseStore(str(tmp_path / "leases.json"), ttl_seconds=1)
    first = store.acquire("e1", "node-a")
    assert first is not None
    time.sleep(1.05)
    second = store.acquire("e1", "node-b")

    assert second is not None
    assert not store.release("e1", "node-a", first.fencing_token)
    assert store.is_owner("e1", "node-b", second.fencing_token)
