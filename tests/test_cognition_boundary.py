import pytest

from cognition.contracts import CognitionDecision, CognitionRequest
from cognition.pipeline import CognitionPipeline
from runtime.execution_context import ExecutionContext


class PlannerStub:
    async def plan(self, request):
        return CognitionDecision("plan", [{"tool": "noop"}])


class StageStub:
    def __init__(self, kind):
        self.kind = kind
        self.seen = []

    async def evaluate(self, request):
        self.seen.append(request)
        return CognitionDecision(self.kind, request.observation)

    async def reflect(self, request):
        self.seen.append(request)
        return CognitionDecision(self.kind, request.observation)

    async def learn(self, request):
        self.seen.append(request)
        return CognitionDecision(self.kind, request.observation)


@pytest.mark.asyncio
async def test_pipeline_uses_one_canonical_execution_context_without_runtime_ownership():
    context = ExecutionContext(execution_id="exec-1", agent_id="agent-1", goal="ship")
    evaluator = StageStub("evaluation")
    reflector = StageStub("reflection")
    learner = StageStub("learning")
    pipeline = CognitionPipeline(PlannerStub(), evaluator, reflector, learner)

    result = await pipeline.run(CognitionRequest(context, observation={"state": "ready"}))

    assert result["plan"].kind == "plan"
    assert all(stage.seen[0].context is context for stage in (evaluator, reflector, learner))
    assert not hasattr(pipeline, "store")
    assert not hasattr(pipeline, "lease_store")
    assert not hasattr(pipeline, "checkpoint")


@pytest.mark.asyncio
async def test_pipeline_can_run_with_only_planner():
    context = ExecutionContext(execution_id="exec-2", goal="inspect")
    result = await CognitionPipeline(PlannerStub()).run(CognitionRequest(context))
    assert result["plan"].value == [{"tool": "noop"}]
    assert result["evaluation"] is None
