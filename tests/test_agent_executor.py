import pytest

from runtime.agent_executor import AgentExecutor
from runtime.execution_audit import ExecutionAudit
from runtime.runtime_orchestrator import RuntimeOrchestrator
from runtime.tool_executor import ToolExecutor
from runtime.tool_registry import ToolRegistry
from runtime.tool_sandbox import ToolSandbox
from runtime.vnext_orchestrator import VNextOrchestrator


async def add(a, b):
    return a + b


class Planner:
    async def create_plan(self, goal):
        return [{"tool": "add", "arguments": {"a": 2, "b": 3}}]


class Agent:
    id = "agent-1"


@pytest.mark.asyncio
async def test_orchestrator_executes_plan_through_tool_boundary():
    registry = ToolRegistry()
    registry.register("add", add, permissions={"compute"})
    audit = ExecutionAudit()
    sandbox = ToolSandbox(registry, audit, authorization={"agent-1": {"compute"}})
    executor = AgentExecutor(ToolExecutor(sandbox))
    runtime = RuntimeOrchestrator(executor=executor, planner=Planner())
    orchestrator = VNextOrchestrator(runtime_orchestrator=runtime, agent=Agent())

    result = await orchestrator.run("calculate", "task-1", {"permissions": ["compute"]})

    assert result.status == "completed"
    assert result.result == [5]
    assert [event.event for event in audit.snapshot()] == [
        "tool.execution.started",
        "tool.execution.completed",
    ]


@pytest.mark.asyncio
async def test_context_cannot_self_grant_unauthorized_permissions():
    registry = ToolRegistry()
    registry.register("add", add, permissions={"compute"})
    sandbox = ToolSandbox(registry, authorization={"agent-1": set()})
    executor = AgentExecutor(ToolExecutor(sandbox))

    result = await executor.execute(
        Agent(),
        [{"tool": "add", "arguments": {"a": 1, "b": 2}}],
        {"permissions": ["compute"]},
    )

    assert result[0].ok is False
    assert "requires permissions" in (result[0].error or "")
