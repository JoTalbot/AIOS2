"""AIOS2 startup validation helpers."""

import importlib
import sys


REQUIRED_MODULES = [
    "fastapi",
    "uvicorn",
]


def validate_startup() -> dict:
    checks = {}

    checks["python"] = "ok" if sys.version_info >= (3, 11) else "warning"

    for module in REQUIRED_MODULES:
        try:
            importlib.import_module(module)
            checks[module] = "ok"
        except ImportError:
            checks[module] = "missing"

    checks["runtime"] = "ok"

    return {
        "system": "AIOS2",
        "status": "ready" if all(value == "ok" for value in checks.values()) else "degraded",
        "checks": checks,
    }


def build_startup_report() -> dict:
    """Compatibility wrapper for operational status reporting."""
    return validate_startup()
