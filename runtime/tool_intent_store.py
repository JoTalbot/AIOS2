"""Durable intent ledger for side-effecting tool calls.

An intent is persisted before the external side effect starts. This turns an
otherwise invisible crash window into an explicit recovery state.
"""
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any, Optional

try:
    import fcntl
except ImportError:  # pragma: no cover
    fcntl = None


AMBIGUOUS_STATES = frozenset({"prepared", "executing", "ambiguous"})


@dataclass(frozen=True)
class ToolIntent:
    idempotency_key: str
    call_id: str
    tool: str
    arguments: Any = field(default_factory=dict)
    execution_id: Optional[str] = None
    state: str = "prepared"
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class _IntentLock:
    def __init__(self, path: Path):
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


class ToolIntentStore:
    def __init__(self, path: str = "data/tool_intents.json"):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.lock_path = self.path.with_suffix(self.path.suffix + ".lock")

    def _read(self):
        if not self.path.exists():
            return {}
        data = json.loads(self.path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError("tool intent store must be an object")
        return data

    def get(self, key):
        if not key:
            return None
        with _IntentLock(self.lock_path):
            raw = self._read().get(key)
        return ToolIntent(**raw) if raw else None

    def prepare(self, intent: ToolIntent):
        with _IntentLock(self.lock_path):
            data = self._read()
            raw = data.get(intent.idempotency_key)
            if raw:
                return ToolIntent(**raw)
            data[intent.idempotency_key] = asdict(intent)
            self._write(data)
            return intent

    def mark(self, key, state):
        with _IntentLock(self.lock_path):
            data = self._read()
            raw = data.get(key)
            if raw is None:
                return None
            raw["state"] = state
            self._write(data)
            return ToolIntent(**raw)

    def pending(self):
        with _IntentLock(self.lock_path):
            return [ToolIntent(**raw) for raw in self._read().values() if raw.get("state") in AMBIGUOUS_STATES]

    def _write(self, data):
        tmp = self.path.with_suffix(self.path.suffix + ".tmp")
        tmp.write_text(json.dumps(data, ensure_ascii=False, default=str, indent=2), encoding="utf-8")
        with tmp.open("r+", encoding="utf-8") as handle:
            handle.flush()
            import os
            os.fsync(handle.fileno())
        tmp.replace(self.path)
