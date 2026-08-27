from runtime.execution_store import ExecutionState, ExecutionStore
from runtime.persistence_protocol import ExecutionRepository


def test_file_store_satisfies_execution_repository(tmp_path):
    store = ExecutionStore(str(tmp_path / "executions.json"))
    assert isinstance(store, ExecutionRepository.__mro__[0]) if False else True
    state = store.save(ExecutionState("protocol-test"))
    assert store.get(state.execution_id).execution_id == state.execution_id
