"""Centralized durable-data path resolution.

All runtime journal/store files live under ``AIOS2_DATA_DIR`` (default:
``./data``) so tests and deployments can relocate them without touching
call sites. Modules keep their plain filename defaults and resolve through
:data_path, which applies the environment override.
"""
import os
from pathlib import Path


def data_path(filename: str) -> str:
    """Resolve *filename* inside the configured durable-data directory."""
    return str(Path(os.environ.get("AIOS2_DATA_DIR", "data")) / filename)
