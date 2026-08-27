from runtime.execution_audit import ExecutionAuditEvent, ExecutionAuditLog
from runtime.execution_store import ExecutionState, ExecutionStore


def test_audit_events_are_read_under_audit_lock(tmp_path, monkeypatch):
    log = ExecutionAuditLog(str(tmp_path / "audit.jsonl"))
    log.append(ExecutionAuditEvent("exec-1", "pending", "running", attempt=1))
    calls = []

    class ObservedFcntl:
        LOCK_EX = 1

        @staticmethod
        def flock(fd, operation):
            calls.append(operation)

    monkeypatch.setattr("runtime.execution_audit.fcntl", ObservedFcntl)
    assert len(log.events("exec-1")) == 1
    assert calls == [ObservedFcntl.LOCK_EX, ObservedFcntl.LOCK_EX]


def test_store_atomic_replace_syncs_parent_directory(tmp_path, monkeypatch):
    store = ExecutionStore(str(tmp_path / "executions.json"))
    calls = []
    monkeypatch.setattr(store, "_fsync_parent_directory", lambda: calls.append(True))
    store.save(ExecutionState("exec-1"))
    assert calls == [True]
