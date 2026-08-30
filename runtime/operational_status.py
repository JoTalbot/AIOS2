"""Unified AIOS2 operational status helpers."""

from .startup_validation import build_startup_report
from .status_report import build_status_report


def build_operational_status() -> dict:
    runtime = build_status_report()
    startup = build_startup_report()
    return {
        "system": "AIOS2",
        "status": "operational",
        "runtime": runtime,
        "startup": startup,
    }
