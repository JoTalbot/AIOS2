"""Durable idempotency registry for tool side-effect results."""

from dataclasses import asdict, dataclass
import json
from pathlib import Path
from typing import Any, Optional

try:
    import fcntl
except ImportError:  # pragma: no cover
    fcntl = None


@dataclass(frozen=True)
class StoredToolResult:
    idempotency_key: str
    call_id: str
    tool: str
    ok: bool
    value: Any = None
    error: Optional[str] = None


class ToolIdempotencyStore:
    def __init__(self, path: str = "data/tool_idempotency.json"):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.lock_path = self.path.with_suffix(self.path.suffix + ".lock")

    def _locked(self):
        return _StoreLock(self.lock_path)

    def _read(self):
        if not self.path.exists():
            return {}
        data = json.loads(self.path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError("tool idempotency store must be an object")
        return data

    def get(self, key: Optional[str]):
        if not key:
            return None
        with self._locked():
            raw = self._read().get(key)
        return StoredToolResult(**raw) if raw else None

    def put_if_absent(self, result: StoredToolResult):
        with self._locked():
            data = self._read()
            if result.idempotency_key in data:
                return StoredToolResult(**data[result.idempotency_key])
            data[result.idempotency_key] = asdict(result)
            tmp = self.path.with_suffix(self.path.suffix + ".tmp")
            tmp.write_text(json.dumps(data, ensure_ascii=False, default=str, indent=2), encoding="utf-8")
            with tmp.open("r+", encoding="utf-8") as handle:
                handle.flush()
                import os
                os.fsync(handle.fileno())
            tmp.replace(self.path)
            return result


class _StoreLock:
    def __init__(self, path):
        self.path = path
        self.handle = None

    def __enter__(self):
        self.path.touch(exist_ok=True)
        self.handle = self.path.open("r+", encoding="utf-8")
        if fcntl is not None:
            fcntl.flock(self.handle.fileno(), fcntl.LOCK_EX)
        return self

    def __exit__(self, exc_type, exc, tb):
        if fcntl is not None:
            fcntl.flock(self.handle.fileno(), fcntl.LOCK_UN)
        self.handle.close()
