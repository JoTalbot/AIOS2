import pytest

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient

from api.app import create_app
from api.security import OperatorRole, SecurityContext
from runtime.recovery_api import RecoveryOperatorService
from runtime.recovery_queue import RecoveryQueue, RecoveryQueueItem


def test_health_readiness_and_diagnostics():
    app = create_app(operator_validator=lambda request: True)
    client = TestClient(app)
    assert client.get("/health").json() == {"status": "ok", "system": "AIOS"}
    assert client.get("/ready").json() == {"status": "ready", "system": "AIOS"}
    diagnostics = client.get("/diagnostics").json()
    assert diagnostics["system"] == "AIOS"
    assert diagnostics["status"] == "operational"
    assert diagnostics["components"]["api"] == "ok"


def test_recovery_auth_receives_request():
    app = create_app(operator_validator=lambda request: request.headers.get("x-operator") == "1")
    client = TestClient(app)
    assert client.get("/recovery/queue").status_code == 403
    assert client.get("/recovery/queue", headers={"x-operator": "1"}).status_code == 200


def test_recovery_queue_rejects_unknown_action():
    app = create_app(operator_validator=lambda request: True)
    client = TestClient(app)
    response = client.get("/recovery/queue", params={"action": "not-an-action"})
    assert response.status_code == 422


def test_recovery_mutation_requires_operator_role(tmp_path):
    queue = RecoveryQueue(str(tmp_path / "recovery.jsonl"))
    queue.enqueue(RecoveryQueueItem("exec-1", "manual_review", "needs review", 1))
    service = RecoveryOperatorService(queue=queue)
    viewer = SecurityContext("viewer", OperatorRole.VIEWER, "corr-viewer")
    app = create_app(recovery_service=service, operator_validator=lambda request: viewer)
    client = TestClient(app)
    response = client.post("/recovery/resolve", json={"execution_id": "exec-1", "action": "manual_review"})
    assert response.status_code == 403
    assert queue.items(unresolved_only=True)[0].resolved is False


def test_recovery_mutation_uses_authenticated_context(tmp_path):
    queue = RecoveryQueue(str(tmp_path / "recovery.jsonl"))
    queue.enqueue(RecoveryQueueItem("exec-1", "manual_review", "needs review", 1))
    service = RecoveryOperatorService(queue=queue)
    operator = SecurityContext("operator-1", OperatorRole.OPERATOR, "corr-123")
    app = create_app(recovery_service=service, operator_validator=lambda request: operator)
    client = TestClient(app)
    response = client.post("/recovery/resolve", json={"execution_id": "exec-1", "action": "manual_review", "reason": "reviewed"})
    assert response.status_code == 200
    assert response.json()["correlation_id"] == "corr-123"
    assert queue.items(unresolved_only=True) == []
