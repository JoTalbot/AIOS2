"""Bounded autonomous execution loop with restart-safe canonical persistence."""

from dataclasses import dataclass
from typing import Any, Optional

from .execution_context import ExecutionContext
from .execution_store import ExecutionState, ExecutionStore
from .event_types import REPLAN_COMPLETED, REPLAN_REQUESTED
from .execution_events import ExecutionEvent
from .replanning import ReplanningPolicy
from .recovery_checkpoint import RecoveryCheckpoint


@dataclass(frozen=True)
class LoopResult:
    status: str
    result: Any = None
    attempts: int = 0


class AutonomousExecutionLoop:
    """Run executions through the injected canonical checkpoint/commit boundary.

    A persistent loop must be constructed with a checkpoint backed by an
    ``ExecutionCommitCoordinator``.  The store-only fallback is intentionally
    limited to ephemeral, non-persistent execution (``store is None``).
    """

    def __init__(self, executor, planner, policy: Optional[ReplanningPolicy] = None, event_bus=None, store: Optional[ExecutionStore] = None, checkpoint: Optional[RecoveryCheckpoint] = None):
        self.executor = executor
        self.planner = planner
        self.policy = policy or ReplanningPolicy()
        self.event_bus = event_bus
        self.store = store
        if store is not None and checkpoint is None:
            raise ValueError("persistent execution requires a canonical checkpoint/commit coordinator")
        self.checkpoint = checkpoint

    async def run(self, goal: str, agent: Any, context: Optional[dict] = None, execution_context: Optional[ExecutionContext] = None):
        context = dict(context or {})
        execution = execution_context or ExecutionContext(agent_id=str(getattr(agent, "id", None) or agent), goal=goal, metadata=context)
        plan = await self.planner.create_plan(goal)
        return await self._run_from_state(goal, agent, context, execution, plan, 0)

    async def resume(self, execution_id: str, agent: Any, context: Optional[dict] = None):
        if not self.store:
            raise RuntimeError("execution store is required for resume")
        state = self.store.get(execution_id)
        if not state or state.status not in {"running", "retrying"}:
            raise ValueError(f"execution '{execution_id}' is not resumable")
        execution = ExecutionContext(execution_id=state.execution_id, agent_id=str(getattr(agent, "id", None) or agent), goal=state.goal, metadata=dict(context or {}))
        return await self._run_from_state(state.goal, agent, dict(context or {}), execution, state.plan, state.attempt)

    async def _run_from_state(self, goal, agent, context, execution, plan, start_attempt):
        state = self.store.get(execution.execution_id) if self.store else None
        if state is None:
            state = ExecutionState(execution.execution_id, status="pending", goal=goal, attempt=start_attempt, plan=plan)
            if self.store:
                self._require_checkpoint()
                self.checkpoint.transition(state, "pending", attempt=start_attempt, plan=plan)

        elif state.status not in {"running", "retrying", "pending"}:
            raise ValueError(f"execution '{state.execution_id}' cannot run from '{state.status}'")

        if state.status in {"pending", "retrying"}:
            state = self._checkpoint_running(state, start_attempt, plan)

        for attempt in range(start_attempt, self.policy.max_attempts):
            if state.attempt != attempt or state.plan != plan:
                state = self._checkpoint_running(state, attempt, plan)
            results = await self.executor.execute(agent, plan, context, execution)
            failed = next((r for r in results if hasattr(r, "ok") and not r.ok), None)
            if failed is None:
                state = self._checkpoint_completed(state, results)
                return LoopResult("completed", results, attempt + 1)
            decision = self.policy.decide(attempt, RuntimeError(failed.error or "tool execution failed"))
            await self._publish(REPLAN_REQUESTED, execution, {"attempt": attempt, "error": failed.error})
            if not decision.retry:
                self._checkpoint_failed(state, failed.error)
                return LoopResult("failed", results, attempt + 1)
            state = self._transition(state, "retrying", attempt=attempt, error=failed.error)
            plan = await self.planner.create_plan(f"{goal} [replan attempt {attempt + 1}]")
            state = self._checkpoint_running(state, attempt + 1, plan)
            await self._publish(REPLAN_COMPLETED, execution, {"attempt": attempt + 1, "plan": plan})
        self._checkpoint_failed(state, "maximum attempts exceeded")
        return LoopResult("failed", attempts=self.policy.max_attempts)

    def _require_checkpoint(self):
        if self.checkpoint is None:
            raise RuntimeError("canonical checkpoint is required for persistent execution")

    def _transition(self, state, status, **updates):
        if self.checkpoint:
            return self.checkpoint.transition(state, status, **updates)
        state.status = status
        for key, value in updates.items():
            setattr(state, key, value)
        return state

    def _checkpoint_running(self, state, attempt, plan):
        if self.checkpoint:
            result = self.checkpoint.mark_running(state, attempt, plan)
            return self.store.get(state.execution_id) if self.store else result
        state.status, state.attempt, state.plan = "running", attempt, plan
        return state

    def _checkpoint_completed(self, state, result):
        if self.checkpoint:
            self.checkpoint.mark_completed(state, result)
            return self.store.get(state.execution_id) if self.store else state
        state.status, state.result, state.error = "completed", result, None
        return state

    def _checkpoint_failed(self, state, error):
        if self.checkpoint:
            self.checkpoint.mark_failed(state, error)
            return self.store.get(state.execution_id) if self.store else state
        state.status, state.error = "failed", str(error)
        return state

    async def _publish(self, event_type, context, data):
        if self.event_bus:
            await self.event_bus.publish(event_type, ExecutionEvent(event_type, context, data))
