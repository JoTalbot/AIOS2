"""Persistent execution state with process-safe optimistic CAS.

The JSON file remains the durable representation, while an adjacent lock file
serializes read/validate/write critical sections.  This prevents two workers
from both validating the same version and then overwriting each other.
"""
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any, Dict, Optional

from .execution_audit import ExecutionAuditEvent, ExecutionAuditLog
from .execution_context import ExecutionContext
from .execution_state_machine import ExecutionStateMachine

try:
    import fcntl
except ImportError:  # pragma: no cover
    fcntl = None


class ExecutionStoreCorruptionError(RuntimeError):
    pass


class ExecutionVersionConflictError(RuntimeError):
    pass


@dataclass
class ExecutionState:
    execution_id: str
    status: str = "pending"
    goal: str = ""
    attempt: int = 0
    plan: Any = None
    result: Any = None
    error: Optional[str] = None
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    correlation_id: Optional[str] = None
    version: int = 0


class _FileLock:
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


class ExecutionStore:
    def __init__(self, path: str = "data/executions.json", state_machine: Optional[ExecutionStateMachine] = None, audit_log: Optional[ExecutionAuditLog] = None):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.lock_path = self.path.with_suffix(self.path.suffix + ".lock")
        self.state_machine = state_machine or ExecutionStateMachine()
        self.audit_log = audit_log
        if not self.path.exists():
            with _FileLock(self.lock_path):
                if not self.path.exists():
                    self._write({})

    def _read_unlocked(self) -> Dict[str, Any]:
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            return {}
        except json.JSONDecodeError as exc:
            raise ExecutionStoreCorruptionError(f"execution store contains invalid JSON: {self.path}") from exc
        if not isinstance(data, dict):
            raise ExecutionStoreCorruptionError(f"execution store must be an object: {self.path}")
        return data

    def _write(self, data):
        tmp = self.path.with_suffix(self.path.suffix + ".tmp")
        tmp.write_text(json.dumps(data, ensure_ascii=False, default=str, indent=2), encoding="utf-8")
        with tmp.open("r+", encoding="utf-8") as handle:
            handle.flush()
            import os
            os.fsync(handle.fileno())
        tmp.replace(self.path)

    def get(self, execution_id):
        with _FileLock(self.lock_path):
            raw = self._read_unlocked().get(execution_id)
        return ExecutionState(**raw) if raw else None

    def save(self, state: ExecutionState):
        with _FileLock(self.lock_path):
            data = self._read_unlocked()
            current = data.get(state.execution_id)
            if current:
                state.version = max(state.version, int(current.get("version", 0))) + 1
            else:
                state.version = max(state.version, 1)
            state.updated_at = datetime.now(timezone.utc).isoformat()
            data[state.execution_id] = asdict(state)
            self._write(data)
        return state

    def compare_and_set(self, state: ExecutionState, expected_version: int):
        with _FileLock(self.lock_path):
            data = self._read_unlocked()
            current = data.get(state.execution_id)
            actual = int(current.get("version", 0)) if current else 0
            if actual != expected_version:
                raise ExecutionVersionConflictError(f"execution {state.execution_id} version {actual} != expected {expected_version}")
            state.version = expected_version + 1
            state.updated_at = datetime.now(timezone.utc).isoformat()
            data[state.execution_id] = asdict(state)
            self._write(data)
        return state

    def transition(self, execution_id, status, *, result=None, error=None):
        state = self.get(execution_id)
        if state is None:
            raise KeyError(execution_id)
        state.status = status
        if result is not None:
            state.result = result
        if error is not None:
            state.error = error
        return self.compare_and_set(state, state.version)

    def resumable(self):
        with _FileLock(self.lock_path):
            data = self._read_unlocked()
        return [ExecutionState(**raw) for raw in data.values() if raw.get("status") in {"pending", "running"}]
