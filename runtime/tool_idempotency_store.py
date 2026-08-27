"""Durable, atomic idempotency registry for completed tool side effects."""
from dataclasses import asdict, dataclass
import json
import os
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


class _StoreLock:
    def __init__(self, path):
        self.path = path
        self.handle = None

    def __enter__(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.touch(exist_ok=True)
        self.handle = self.path.open("r+", encoding="utf-8")
        if fcntl is not None:
            fcntl.flock(self.handle.fileno(), fcntl.LOCK_EX)
        return self

    def __exit__(self, exc_type, exc, tb):
        if fcntl is not None:
            fcntl.flock(self.handle.fileno(), fcntl.LOCK_UN)
        self.handle.close()


class ToolIdempotencyStore:
    def __init__(self, path: str = "data/tool_idempotency.json"):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.lock_path = self.path.with_suffix(self.path.suffix + ".lock")

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
        with _StoreLock(self.lock_path):
            raw = self._read().get(key)
        return StoredToolResult(**raw) if raw else None

    def put_if_absent(self, result: StoredToolResult):
        if not isinstance(result, StoredToolResult) or not result.idempotency_key:
            raise ValueError("valid StoredToolResult with idempotency_key is required")
        with _StoreLock(self.lock_path):
            data = self._read()
            raw = data.get(result.idempotency_key)
            if raw:
                existing = StoredToolResult(**raw)
                if (existing.call_id, existing.tool) != (result.call_id, result.tool):
                    raise ValueError("idempotency key is bound to a different tool call")
                return existing
            data[result.idempotency_key] = asdict(result)
            tmp = self.path.with_suffix(self.path.suffix + ".tmp")
            try:
                with tmp.open("w", encoding="utf-8") as handle:
                    json.dump(data, handle, ensure_ascii=False, default=str, indent=2)
                    handle.flush()
                    os.fsync(handle.fileno())
                os.replace(tmp, self.path)
                directory = self.path.parent.open("rb")
                try:
                    os.fsync(directory.fileno())
                finally:
                    directory.close()
            finally:
                if tmp.exists():
                    tmp.unlink()
            return result
