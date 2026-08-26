"""AIOS vNext orchestration facade over the canonical runtime lifecycle."""

from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from .execution_context import ExecutionContext
from .orchestration_events import OrchestrationEvents


@dataclass
class OrchestrationResult:
    goal: str
    task_id: str
    status: str
    result: Any = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class VNextOrchestrator:
    """Expose the vNext Intent -> Execution -> Reflection -> Memory boundary.

    RuntimeOrchestrator owns execution lifecycle, persistence, leases, recovery,
    and tool execution. This class is deliberately a facade and must not create
    a second scheduler/execution world.
    """

    def __init__(self, runtime_orchestrator, agent, reflection=None, memory=None, event_bus=None):
        self.runtime = runtime_orchestrator
        self.agent = agent
        self.reflection = reflection
        self.memory = memory
        self.events = OrchestrationEvents(event_bus)

    async def run(self, goal: str, task_id: str, metadata: Optional[Dict[str, Any]] = None):
        context = dict(metadata or {})
        execution = ExecutionContext(agent_id=str(getattr(self.agent, "id", None) or self.agent), goal=goal, metadata=context)
        await self.events.started(execution, task_id=task_id)
        try:
            result = await self.runtime.execute(goal, self.agent, context=context)
            context["execution_id"] = self._execution_id(result, execution.execution_id)
            if self.memory and hasattr(self.memory, "remember"):
                self.memory.remember({"event": "task.completed", "execution_id": context["execution_id"], "task_id": task_id, "goal": goal, "result": result.result})
                await self.events.memory_updated(execution, kind="result", task_id=task_id)
            if self.reflection:
                await self.events.reflection_started(execution, task_id=task_id)
                context["reflection"] = await self.reflection.evaluate([result.result])
                await self.events.reflection_completed(execution, task_id=task_id)
            if result.status == "completed":
                await self.events.completed(execution, task_id=task_id)
            else:
                await self.events.failed(execution, task_id=task_id, reason=result.status)
            return OrchestrationResult(goal, task_id, result.status, result.result, context)
        except Exception as exc:
            await self.events.failed(execution, task_id=task_id, error=str(exc))
            raise

    @staticmethod
    def _execution_id(result, fallback):
        return getattr(result, "execution_id", None) or fallback
