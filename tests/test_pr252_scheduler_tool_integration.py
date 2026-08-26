import asyncio

from kernel.scheduler import AgentTask, Scheduler, TaskState
from runtime.agent_executor import AgentExecutor
from runtime.tool_executor import ToolExecutor
from runtime.tool_registry import ToolRegistry
from runtime.tool_sandbox import ToolSandbox


def test_scheduler_agent_executor_tool_boundary():
    async def scenario():
        calls = []
        registry = ToolRegistry()

        async def echo(value):
            calls.append(value)
            return {"echo": value}

        registry.register("echo", echo, permissions={"tool:echo"})
        sandbox = ToolSandbox(registry, authorization={"agent-1": {"tool:echo"}})
        executor = AgentExecutor(ToolExecutor(sandbox))
        scheduler = Scheduler()
        task = AgentTask(
            "integration-1", "agent-1", {
                "agent": "agent-1",
                "plan": [{"tool": "echo", "arguments": {"value": "ok"}}],
                "context": {"goal": "echo", "permissions": {"tool:echo"}},
                "executor": executor,
            }
        )
        await scheduler.submit(task)
        await scheduler.run_until_idle()

        assert task.state is TaskState.DONE
        assert calls == ["ok"]
        assert task.payload["result"][0].ok
        assert task.payload["result"][0].value == {"echo": "ok"}

    asyncio.run(scenario())
