"""Composition of cognition components without owning runtime lifecycle state."""

from typing import Any, Optional

from .contracts import CognitionDecision, CognitionRequest, Evaluator, Learner, Planner, Reflector


class CognitionPipeline:
    """Runs cognition stages against one canonical execution context.

    This component is deliberately ephemeral: it does not acquire leases, mutate
    execution state, persist checkpoints, recover work, or execute tools.
    """

    def __init__(self, planner: Planner, evaluator: Optional[Evaluator] = None,
                 reflector: Optional[Reflector] = None, learner: Optional[Learner] = None):
        self.planner = planner
        self.evaluator = evaluator
        self.reflector = reflector
        self.learner = learner

    async def plan(self, request: CognitionRequest) -> CognitionDecision:
        return await self.planner.plan(request)

    async def evaluate(self, request: CognitionRequest) -> Optional[CognitionDecision]:
        if self.evaluator is None:
            return None
        return await self.evaluator.evaluate(request)

    async def reflect(self, request: CognitionRequest) -> Optional[CognitionDecision]:
        if self.reflector is None:
            return None
        return await self.reflector.reflect(request)

    async def learn(self, request: CognitionRequest) -> Optional[CognitionDecision]:
        if self.learner is None:
            return None
        return await self.learner.learn(request)

    async def run(self, request: CognitionRequest) -> dict[str, Any]:
        plan = await self.plan(request)
        observation = plan.value
        evaluated = await self.evaluate(CognitionRequest(request.context, observation, request.history))
        reflected = await self.reflect(CognitionRequest(request.context, evaluated or observation, request.history))
        learned = await self.learn(CognitionRequest(request.context, reflected or evaluated or observation, request.history))
        return {"plan": plan, "evaluation": evaluated, "reflection": reflected, "learning": learned}
