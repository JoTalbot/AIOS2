"""Uvicorn entrypoint for the AIOS control plane."""
import hmac
import os
from .app import create_app
from .security import authenticate

def operator_validator(request):
    """Legacy boolean validator; the application uses canonical fail-closed auth."""
    supplied = request.headers.get("authorization", "")
    expected = os.getenv("AIOS_OPERATOR_TOKEN", "")
    if not supplied.startswith("Bearer ") or not expected:
        return False
    return hmac.compare_digest(supplied[7:], expected)

app = create_app(operator_validator=authenticate)
