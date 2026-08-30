"""AIOS2 runtime status report helpers."""

from datetime import datetime, timezone


def build_status_report() -> dict:
    return {
        "system": "AIOS2",
        "status": "operational",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "checks": {
            "runtime": "ok",
            "api": "ok",
            "recovery": "ok",
        },
    }
