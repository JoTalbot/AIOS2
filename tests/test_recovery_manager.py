import pytest

from runtime.execution_store import ExecutionState, ExecutionStore
from runtime.recovery_manager import RecoveryManager


class Loop:
    def __init__(self):
        self.calls = []

    async def run(self, goal, agent, context=None, execution_context=None):
        self.calls.append((goal, agent))
        return "resumed"


@pytest.mark.asyncio
async def test_recovery_manager_resumes_pending_executions(tmp_path):
    store = ExecutionStore(str(tmp_path / "executions.json"))
    store.save(ExecutionState("e1", status="running", goal="finish task"))
    store.save(ExecutionState("e2", status="completed", goal="already done"))

    loop = Loop()
    results = await RecoveryManager(store).recover(loop, "agent-1")

    assert results == [("e1", "resumed")]
    assert loop.calls == [("finish task", "agent-1")]


def test_recovery_manager_marks_failed_execution(tmp_path):
    store = ExecutionStore(str(tmp_path / "executions.json"))
    state = store.save(ExecutionState("e1", status="running"))
    updated = RecoveryManager(store).mark_failed(state, RuntimeError("crash"))
    assert updated.status == "failed"
    assert updated.error == "crash"


@pytest.mark.asyncio
async def test_recovery_manager_isolates_one_failed_resume(tmp_path):
    store = ExecutionStore(str(tmp_path / "executions.json"))
    store.save(ExecutionState("bad", status="running"))
    store.save(ExecutionState("good", status="retrying"))

    class FlakyLoop:
        async def resume(self, execution_id, agent, context=None):
            if execution_id == "bad":
                raise RuntimeError("resume failed")
            return "ok"

    results = await RecoveryManager(store).recover(FlakyLoop(), "agent")

    assert results == [("good", "ok")]
    assert store.get("bad").status == "failed"
    assert store.get("bad").error == "resume failed"
    assert store.get("good").status == "retrying"


@pytest.mark.asyncio
async def test_recovery_manager_can_fail_fast(tmp_path):
    store = ExecutionStore(str(tmp_path / "executions.json"))
    state = store.save(ExecutionState("bad", status="running"))

    class BrokenLoop:
        async def resume(self, execution_id, agent, context=None):
            raise RuntimeError("boom")

    with pytest.raises(RuntimeError, match="boom"):
        await RecoveryManager(store).recover(BrokenLoop(), "agent", continue_on_error=False)
    assert store.get(state.execution_id).status == "failed"
