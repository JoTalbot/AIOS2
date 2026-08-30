import json
from pathlib import Path

import pytest

from runtime.execution_store import ExecutionState, ExecutionStore, ExecutionVersionConflictError


def test_cas_serializes_writers(tmp_path):
    path = tmp_path / "executions.json"
    store = ExecutionStore(str(path))
    state = store.save(ExecutionState("e1"))
    writer_a = store.get("e1")
    writer_b = store.get("e1")

    writer_a.status = "running"
    store.compare_and_set(writer_a, state.version)

    writer_b.status = "running"
    with pytest.raises(ExecutionVersionConflictError):
        store.compare_and_set(writer_b, state.version)

    assert store.get("e1").version == 2


def test_failed_temp_write_does_not_replace_durable_state(tmp_path, monkeypatch):
    path = tmp_path / "executions.json"
    store = ExecutionStore(str(path))
    state = store.save(ExecutionState("e1"))
    before = json.loads(path.read_text())

    def fail_replace(src, dst):
        raise OSError("simulated crash before rename")

    monkeypatch.setattr(Path, "replace", fail_replace)
    state.status = "running"
    with pytest.raises(OSError):
        store.compare_and_set(state, state.version)

    assert json.loads(path.read_text()) == before
    assert not path.with_suffix(path.suffix + ".tmp").exists()
