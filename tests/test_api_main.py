import pytest

fastapi = pytest.importorskip("fastapi")
from fastapi.testclient import TestClient

from api.main import operator_validator
from api.app import create_app


def test_operator_validator_requires_bearer_token(monkeypatch):
    monkeypatch.setenv("AIOS_OPERATOR_TOKEN", "secret")
    class Request:
        headers = {"authorization": "Bearer secret"}
    assert operator_validator(Request()) is True


def test_operator_validator_rejects_wrong_token(monkeypatch):
    monkeypatch.setenv("AIOS_OPERATOR_TOKEN", "secret")
    class Request:
        headers = {"authorization": "Bearer wrong"}
    assert operator_validator(Request()) is False
