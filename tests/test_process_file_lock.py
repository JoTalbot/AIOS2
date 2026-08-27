import multiprocessing

from runtime.lease_lock import ProcessFileLock


def _worker(path):
    lock = ProcessFileLock(path)
    with lock.acquire():
        with open(path + ".counter", "a", encoding="utf-8") as handle:
            handle.write("x")


def test_process_file_lock_serializes_workers(tmp_path):
    path = str(tmp_path / "state.lock")
    processes = [multiprocessing.Process(target=_worker, args=(path,)) for _ in range(4)]
    for process in processes:
        process.start()
    for process in processes:
        process.join()
        assert process.exitcode == 0
    assert (tmp_path / "state.lock.counter").read_text(encoding="utf-8") == "xxxx"
