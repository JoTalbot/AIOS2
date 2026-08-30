import json

import pytest

from runtime.execution_store import ExecutionState, ExecutionStore, ExecutionVersionConflictError


def test_compare_and_set_rejects_stale_version(tmp_path):
    path = tmp_path / "executions.json"
    store_a = ExecutionStore(str(path))
    store_b = ExecutionStore(str(path))
    first = store_a.save(ExecutionState("exec-1", goal="one"))
    store_b.transition("exec-1", "running")
    first.status = "completed"
    with pytest.raises(ExecutionVersionConflictError):
        store_a.compare_and_set(first, first.version)


def test_atomic_replace_preserves_previous_file_when_replace_fails(tmp_path, monkeypatch):
    path = tmp_path / "executions.json"
    store = ExecutionStore(str(path))
    store.save(ExecutionState("exec-1", goal="stable"))
    before = path.read_text(encoding="utf-8")
    original_replace = type(path).replace

    def fail_replace(self, target):
        if self.name.endswith(".tmp"):
            raise OSError("simulated crash before replace")
        return original_replace(self, target)

    monkeypatch.setattr(type(path), "replace", fail_replace)
    with pytest.raises(OSError, match="simulated crash"):
        store.save(ExecutionState("exec-1", goal="new"))
    assert path.read_text(encoding="utf-8") == before
    assert json.loads(path.read_text(encoding="utf-8"))["exec-1"]["goal"] == "stable"


def test_failed_atomic_write_does_not_leave_tmp_file(tmp_path, monkeypatch):
    path = tmp_path / "executions.json"
    store = ExecutionStore(str(path))

    def fail_replace(self, target):
        raise OSError("simulated crash")

    monkeypatch.setattr(type(path), "replace", fail_replace)
    with pytest.raises(OSError):
        store.save(ExecutionState("exec-1"))
    assert not path.with_suffix(path.suffix + ".tmp").exists()
