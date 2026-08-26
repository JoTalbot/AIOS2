import pytest

from runtime.autonomous_loop import AutonomousExecutionLoop
from runtime.execution_store import ExecutionContext, ExecutionState, ExecutionStore
from runtime.replanning import ReplanningPolicy
from runtime.tool_protocol import ToolResult


class Planner:
    async def create_plan(self, goal):
        return [{"tool": "work", "arguments": {"goal": goal}}]


class Runner:
    def __init__(self):
        self.calls = 0

    async def execute(self, agent, plan, context, execution):
        self.calls += 1
        return [ToolResult("resume-call", "work", True, value="recovered")]


@pytest.mark.asyncio
async def test_fresh_runtime_recovers_persisted_execution_and_executes_once(tmp_path):
    store = ExecutionStore(str(tmp_path / "executions.json"))
    execution_id = "fresh-runtime-1"
    store.save(
        ExecutionState(
            execution_id,
            status="running",
            goal="resume task",
            attempt=0,
            plan=[{"tool": "work", "arguments": {"goal": "resume task"}}],
        )
    )

    runner = Runner()
    fresh_loop = AutonomousExecutionLoop(
        runner,
        Planner(),
        ReplanningPolicy(max_attempts=2),
        store=store,
    )

    restored = await fresh_loop.resume(execution_id, "agent-1")

    assert restored.status == "completed"
    assert runner.calls == 1
    assert store.get(execution_id).status == "completed"

    # A second recovery attempt must not replay a completed execution.
    with pytest.raises(ValueError, match="not resumable"):
        await fresh_loop.resume(execution_id, "agent-1")
    assert runner.calls == 1
