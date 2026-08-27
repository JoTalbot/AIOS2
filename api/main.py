"""Uvicorn entrypoint for the AIOS control plane."""
from .app import create_app
from .security import authenticate


def operator_validator(request):
    """Backward-compatible boolean validator for legacy callers/tests.

    The application itself uses ``authenticate`` for real authorization; this
    helper only preserves the historical "has a bearer credential" contract.
    """
    authorization = getattr(request, "headers", {}).get("authorization", "")
    return authorization.startswith("Bearer ") or bool(authorization)


app = create_app(operator_validator=authenticate)
