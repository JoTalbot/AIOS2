"""Small async scheduler compatibility layer used by the vNext orchestrator."""
from dataclasses import dataclass, field
from enum import Enum

class TaskState(str, Enum):
    PENDING="pending"; RUNNING="running"; DONE="done"; FAILED="failed"

@dataclass
class AgentTask:
    id: str
    agent: str
    payload: dict = field(default_factory=dict)
    state: TaskState = TaskState.PENDING

class Scheduler:
    def __init__(self): self.tasks=[]
    async def submit(self, task): self.tasks.append(task); return task
    async def execute(self, task):
        if task.state is not TaskState.PENDING: return task
        task.state = TaskState.RUNNING
        try:
            executor = task.payload.get("executor")
            if executor is not None:
                task.payload["result"] = await executor.execute(task.payload["agent"], task.payload.get("plan", ()), task.payload.get("context", {}), execution_context=task.payload.get("execution_context"))
            task.state = TaskState.DONE
            return task
        except Exception:
            task.state = TaskState.FAILED
            raise
    async def run_until_idle(self):
        for task in self.tasks:
            await self.execute(task)
        return list(self.tasks)
