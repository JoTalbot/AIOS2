import pytest

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient

from api.app import create_app


def test_production_smoke_endpoints():
    app = create_app(operator_validator=lambda request: True)
    client = TestClient(app)

    assert client.get("/health").status_code == 200
    assert client.get("/ready").status_code == 200

    diagnostics = client.get("/diagnostics")
    assert diagnostics.status_code == 200
    assert diagnostics.json()["system"] == "AIOS"
