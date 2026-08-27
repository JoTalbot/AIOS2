from runtime.execution_audit import ExecutionAuditEvent, ExecutionAuditLog
from runtime.execution_store import ExecutionState, ExecutionStore


def test_audit_events_are_read_under_audit_lock(tmp_path, monkeypatch):
    log = ExecutionAuditLog(str(tmp_path / "audit.jsonl"))
    log.append(ExecutionAuditEvent("exec-1", "pending", "running", attempt=1))
    calls = []

    class ObservedLock:
        def __enter__(self):
            calls.append("enter")
            return self

        def __exit__(self, *args):
            calls.append("exit")
            return False

    monkeypatch.setattr(log, "lock_path", tmp_path / "observed.lock")
    monkeypatch.setattr("runtime.execution_audit.fcntl", None)
    original_open = log.lock_path.open

    class LockPath:
        def open(self, *args, **kwargs):
            return ObservedLock()

    monkeypatch.setattr(log, "lock_path", LockPath())
    assert len(log.events("exec-1")) == 1
    assert calls == ["enter", "exit"]


def test_store_atomic_replace_syncs_parent_directory(tmp_path, monkeypatch):
    store = ExecutionStore(str(tmp_path / "executions.json"))
    calls = []
    monkeypatch.setattr(store, "_fsync_parent_directory", lambda: calls.append(True))
    store.save(ExecutionState("exec-1"))
    assert calls == [True]
