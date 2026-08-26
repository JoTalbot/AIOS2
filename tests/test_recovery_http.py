import pytest

fastapi = pytest.importorskip("fastapi")
from fastapi.testclient import TestClient

from api.app import create_app
from runtime.recovery_api import RecoveryOperatorService
from runtime.recovery_queue import RecoveryQueue, RecoveryQueueItem


def test_operator_boundary_and_queue(tmp_path):
    queue = RecoveryQueue(str(tmp_path / "queue.jsonl"))
    queue.enqueue(RecoveryQueueItem("e1", "manual_review", "needs operator", 3))
    app = create_app(recovery_service=RecoveryOperatorService(queue), operator_validator=lambda request: request.headers.get("x-operator") == "1")
    client = TestClient(app)

    assert client.get("/recovery/manual-review").status_code == 403
    response = client.get("/recovery/manual-review", headers={"x-operator": "1"})
    assert response.status_code == 200
    assert response.json()[0]["execution_id"] == "e1"
