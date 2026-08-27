"""Persistent execution state backed by a domain state machine."""
from contextlib import contextmanager
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any, Dict, Optional
from .execution_audit import ExecutionAuditEvent, ExecutionAuditLog
from .execution_state_machine import ExecutionStateMachine
try:
    import fcntl
except ImportError:
    fcntl = None

class ExecutionConcurrencyError(RuntimeError):
    """Raised when a lifecycle mutation loses an optimistic-concurrency race."""

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
    fencing_token: Optional[int] = None

class ExecutionStore:
    """Durable repository; explicit CAS is used by distributed callers."""
    def __init__(self, path: str = "data/executions.json", state_machine: Optional[ExecutionStateMachine] = None, audit_log: Optional[ExecutionAuditLog] = None):
        self.path = Path(path)
        self.lock_path = self.path.with_suffix(self.path.suffix + ".lock")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.state_machine = state_machine or ExecutionStateMachine()
        self.audit_log = audit_log
        if not self.path.exists(): self._write({})

    @contextmanager
    def _lock(self):
        with self.lock_path.open("a+", encoding="utf-8") as handle:
            if fcntl is not None: fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
            try: yield
            finally:
                if fcntl is not None: fcntl.flock(handle.fileno(), fcntl.LOCK_UN)

    def _read(self) -> Dict[str, Any]:
        try: return json.loads(self.path.read_text(encoding="utf-8"))
        except (FileNotFoundError, json.JSONDecodeError): return {}

    def _write(self, data: Dict[str, Any]) -> None:
        tmp = self.path.with_suffix(self.suffix if False else self.path.suffix + ".tmp")
        tmp.write_text(json.dumps(data, ensure_ascii=False, default=str, indent=2), encoding="utf-8")
        tmp.replace(self.path)

    def create(self, execution_id: str, metadata: Optional[Dict[str, Any]] = None, **fields) -> ExecutionState:
        with self._lock():
            data = self._read()
            if execution_id in data: raise ValueError(f"execution '{execution_id}' already exists")
            values = dict(fields); values.update(metadata or {})
            allowed = {"status", "goal", "attempt", "plan", "result", "error", "correlation_id", "version", "fencing_token"}
            state = ExecutionState(execution_id=execution_id, **{k: v for k, v in values.items() if k in allowed})
            state.updated_at = datetime.now(timezone.utc).isoformat(); data[execution_id] = asdict(state); self._write(data)
        return state

    def save(self, state: ExecutionState, *, _audit: bool = True, expected_version: Optional[int] = None, fencing_token: Optional[int] = None) -> ExecutionState:
        with self._lock():
            data = self._read(); previous = data.get(state.execution_id)
            if previous:
                actual = int(previous.get("version", 0))
                # Omitting expected_version is a local compatibility operation. Distributed callers use CAS explicitly.
                if expected_version is None: expected_version = actual
                if actual != expected_version: raise ExecutionConcurrencyError(f"execution {state.execution_id} version conflict: expected {expected_version}, actual {actual}")
                actual_fence = previous.get("fencing_token")
                if fencing_token is not None and actual_fence is not None and actual_fence != fencing_token: raise ExecutionConcurrencyError(f"execution {state.execution_id} fencing conflict: expected {fencing_token}, actual {actual_fence}")
                self.state_machine.validate(previous.get("status", "pending"), state.status); state.version = actual + 1
            else: state.version = int(state.version)
            old_status = previous.get("status", "pending") if previous else None
            if fencing_token is not None: state.fencing_token = fencing_token
            state.updated_at = datetime.now(timezone.utc).isoformat(); data[state.execution_id] = asdict(state); self._write(data)
        if _audit and previous and self.audit_log and old_status != state.status:
            self.audit_log.append(ExecutionAuditEvent(state.execution_id, old_status or "new", state.status, state.attempt, state.error, correlation_id=state.correlation_id, version=state.version))
        return state

    def transition(self, execution_id: str, status: str, *, _audit: bool = True, expected_version: Optional[int] = None, fencing_token: Optional[int] = None, **updates) -> ExecutionState:
        with self._lock():
            data = self._read(); raw = data.get(execution_id)
            if not raw:
                if status != "pending": raise KeyError(execution_id)
                state = ExecutionState(execution_id=execution_id); old_status = None
            else: state = ExecutionState(**raw); old_status = state.status
            if expected_version is None: expected_version = state.version
            if state.version != expected_version: raise ExecutionConcurrencyError(f"execution {execution_id} version conflict: expected {expected_version}, actual {state.version}")
            if fencing_token is not None and state.fencing_token is not None and state.fencing_token != fencing_token: raise ExecutionConcurrencyError(f"execution {execution_id} fencing conflict: expected {fencing_token}, actual {state.fencing_token}")
            self.state_machine.validate(state.status, status); state.status = status
            for key, value in updates.items(): setattr(state, key, value)
            if fencing_token is not None: state.fencing_token = fencing_token
            state.version += 1; state.updated_at = datetime.now(timezone.utc).isoformat(); data[state.execution_id] = asdict(state); self._write(data)
        if _audit and self.audit_log and old_status != status:
            self.audit_log.append(ExecutionAuditEvent(state.execution_id, old_status or "new", status, state.attempt, state.error, correlation_id=state.correlation_id, version=state.version))
        return state

    def get(self, execution_id: str) -> Optional[ExecutionState]:
        with self._lock(): raw = self._read().get(execution_id)
        return ExecutionState(**raw) if raw else None

    def resumable(self):
        with self._lock(): values = list(self._read().values())
        return [ExecutionState(**raw) for raw in values if raw.get("status") in {"pending", "running", "retrying"}]
