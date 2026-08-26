import importlib


def test_api_main_exports_app():
    module = importlib.import_module("api.main")
    assert module.app is not None


def test_operator_auth_ci_token_meets_config_contract(monkeypatch):
    from api.auth_config import ControlPlaneAuthConfig
    monkeypatch.setenv("AIOS_OPERATOR_TOKEN", "ci-test-token-16")
    monkeypatch.setenv("AIOS_OPERATOR_ROLE", "operator")
    monkeypatch.setenv("AIOS_OPERATOR_ACTOR", "ci")
    config = ControlPlaneAuthConfig.from_env()
    assert config.role == "operator"


def test_scheduler_executor_contract_accepts_execution_context():
    from kernel.scheduler import Scheduler
    assert hasattr(Scheduler, "execute")
