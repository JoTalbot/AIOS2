"""AIOS vNext end-to-end orchestration boundary."""

from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from .agent_executor import AgentExecutor
from .execution_context import ExecutionContext
from .orchestration_events import OrchestrationEvents
from cognition.contracts import CognitionDecision, CognitionRequest
from cognition.pipeline import CognitionPipeline


@dataclass
class OrchestrationResult:
    goal: str
    task_id: str
    status: str
    result: Any = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class VNextOrchestrator:
    """Coordinates Intent -> Planner -> Scheduler -> Agent -> Tools -> Memory -> Reflection."""

    def __init__(self, planner, scheduler, agent, reflection=None, executor: Optional[AgentExecutor] = None, memory=None, event_bus=None, cognition: Optional[CognitionPipeline] = None):
        self.planner = planner
        self.scheduler = scheduler
        self.agent = agent
        self.reflection = reflection
        self.executor = executor
        self.memory = memory
        self.events = OrchestrationEvents(event_bus)
        self.cognition = cognition

    async def run(self, goal: str, task_id: str, metadata: Optional[Dict[str, Any]] = None):
        context = dict(metadata or {})
        execution = ExecutionContext(agent_id=str(getattr(self.agent, "id", None) or self.agent), goal=goal, metadata=context)
        await self.events.started(execution, task_id=task_id)
        try:
            if self.cognition is not None:
                decision = await self.cognition.plan(CognitionRequest(execution, history=tuple(execution.events)))
                plan = decision.value
                context["cognition_plan"] = decision
            else:
                plan = await self.planner.create_plan(goal)
            context["plan"] = plan
            await self.events.plan_created(execution, task_id=task_id, plan=plan)
            if self.memory and hasattr(self.memory, "remember"):
                self.memory.remember({"event": "plan.created", "execution_id": execution.execution_id, "task_id": task_id, "goal": goal, "plan": plan})
                await self.events.memory_updated(execution, kind="plan", task_id=task_id)
            task = self._build_task(task_id, goal, plan, context, execution)
            await self.scheduler.submit(task)
            await self.scheduler.run_until_idle()
            if getattr(task, "state", None).value == "failed":
                await self.events.failed(execution, task_id=task_id, reason="scheduler_task_failed")
                return OrchestrationResult(goal, task_id, "failed", metadata=context)
            result = getattr(task, "payload", {}).get("result")
            if self.cognition is not None:
                cognition_result = await self.cognition.evaluate(CognitionRequest(execution, observation=result, history=tuple(execution.events)))
                if cognition_result is not None:
                    context["cognition_evaluation"] = cognition_result
            if self.reflection:
                await self.events.reflection_started(execution, task_id=task_id)
                context["reflection"] = await self.reflection.evaluate([result])
                await self.events.reflection_completed(execution, task_id=task_id)
            if self.cognition is not None:
                cognition_reflection = await self.cognition.reflect(CognitionRequest(execution, observation=context.get("cognition_evaluation", result), history=tuple(execution.events)))
                if cognition_reflection is not None:
                    context["cognition_reflection"] = cognition_reflection
                cognition_learning = await self.cognition.learn(CognitionRequest(execution, observation=context.get("cognition_reflection", cognition_reflection or result), history=tuple(execution.events)))
                if cognition_learning is not None:
                    context["cognition_learning"] = cognition_learning
            if self.memory and hasattr(self.memory, "remember"):
                self.memory.remember({"event": "task.completed", "execution_id": execution.execution_id, "task_id": task_id, "result": result})
                await self.events.memory_updated(execution, kind="result", task_id=task_id)
            await self.events.completed(execution, task_id=task_id)
            context["execution_id"] = execution.execution_id
            return OrchestrationResult(goal, task_id, "completed", result, context)
        except Exception as exc:
            await self.events.failed(execution, task_id=task_id, error=str(exc))
            raise

    def _build_task(self, task_id, goal, plan, context, execution_context=None):
        from kernel.scheduler import AgentTask
        payload = {"goal": goal, "plan": plan, "context": context, "agent": self.agent, "execution_context": execution_context}
        if self.executor:
            payload["executor"] = self.executor
        return AgentTask(id=task_id, agent=str(self.agent), payload=payload)
