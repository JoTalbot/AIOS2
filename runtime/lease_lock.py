"""Cross-process lock for file-backed runtime state."""
from contextlib import contextmanager
from pathlib import Path
import os

try:
    import fcntl
except ImportError:  # pragma: no cover
    fcntl = None


class ProcessFileLock:
    """Serialize read-modify-write operations across worker processes."""
    def __init__(self, path: str):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    @contextmanager
    def acquire(self):
        if fcntl is None:
            yield
            return
        handle = self.path.open("a+", encoding="utf-8")
        try:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
            yield
        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
            handle.close()
