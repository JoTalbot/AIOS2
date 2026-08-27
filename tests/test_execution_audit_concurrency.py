import threading

from runtime.execution_audit import ExecutionAuditEvent, ExecutionAuditLog


def test_concurrent_audit_reads_and_writes_are_consistent(tmp_path):
    audit = ExecutionAuditLog(str(tmp_path / "audit.jsonl"))
    writers = 8
    per_writer = 10
    barrier = threading.Barrier(writers)
    errors = []
    observed = []
    lock = threading.Lock()

    def writer(worker):
        try:
            barrier.wait(timeout=5)
            for index in range(per_writer):
                audit.append(ExecutionAuditEvent("e1", "pending", "running", worker, reason=str(index)))
        except Exception as exc:
            with lock:
                errors.append(exc)

    def reader():
        try:
            for _ in range(writers * per_writer):
                events = audit.events("e1")
                with lock:
                    observed.append(len(events))
                assert all(event.execution_id == "e1" for event in events)
        except Exception as exc:
            with lock:
                errors.append(exc)

    threads = [threading.Thread(target=writer, args=(worker,), daemon=True) for worker in range(writers)]
    threads.append(threading.Thread(target=reader, daemon=True))
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=15)

    assert not errors
    assert all(not thread.is_alive() for thread in threads)
    events = audit.events("e1")
    assert len(events) == writers * per_writer
    assert len({event.event_id for event in events}) == len(events)
    assert observed
