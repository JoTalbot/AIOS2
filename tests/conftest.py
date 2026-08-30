"""Shared test configuration for AIOS2.

Redirects every durable runtime file (default ``./data``) into a
session-scoped temporary directory so test runs never mutate tracked
repository data. conftest is imported before test modules, so the
environment override is in place before the API app and any store with
default paths are constructed.

Relative paths passed explicitly by tests (e.g. ``tmp_path`` fixtures) are
unaffected.
"""
import os
import tempfile

_TEST_DATA_DIR = tempfile.mkdtemp(prefix="aios2-test-data-")
os.environ["AIOS2_DATA_DIR"] = _TEST_DATA_DIR
