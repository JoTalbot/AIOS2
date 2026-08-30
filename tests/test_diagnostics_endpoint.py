import pytest

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient

from api.app import create_app


def test_diagnostics_endpoint():
    app = create_app(operator_validator=lambda request: True)
    client = TestClient(app)

    response = client.get("/diagnostics")

    assert response.status_code == 200
    assert response.json()["system"] == "AIOS"
    assert response.json()["status"] == "operational"
    assert response.json()["components"]["api"] == "ok"
