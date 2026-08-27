import pytest

from runtime.recovery_orchestrator import RecoveryOrchestrator
from runtime.recovery_outcome import RecoveryOutcome


class FakeManager:
    def __init__(self, events):
        self.events = events

    async def recover(self, loop, agent, context=None, *, continue_on_error=True):
        self.events.append("recover")
        return [RecoveryOutcome("e2", "recovered")]


class FakeCoordinator:
    def __init__(self, events):
        self.events = events

    def reconcile(self):
        self.events.append("reconcile")
        return ["e1:1:completed:"]


@pytest.mark.asyncio
async def test_reconcile_happens_before_resume():
    events = []
    report = await RecoveryOrchestrator(
        FakeManager(events), FakeCoordinator(events)
    ).recover(object(), object(), context={"boot": True})

    assert events == ["reconcile", "recover"]
    assert report.reconciled_commit_ids == ("e1:1:completed:",)
    assert report.recovered == 1
    assert report.failed == 0


@pytest.mark.asyncio
async def test_orchestrator_without_commit_coordinator_preserves_manager_flow():
    events = []
    report = await RecoveryOrchestrator(FakeManager(events)).recover(object(), object())

    assert events == ["recover"]
    assert report.reconciled_commit_ids == ()
    assert report.outcomes == (RecoveryOutcome("e2", "recovered"),)
