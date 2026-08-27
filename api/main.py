"""Uvicorn entrypoint for the AIOS control plane."""
from .app import create_app
from .security import authenticate


def operator_validator(request):
    """Backward-compatible boolean validator using canonical authentication."""
    return authenticate(request) is not None


app = create_app(operator_validator=authenticate)
