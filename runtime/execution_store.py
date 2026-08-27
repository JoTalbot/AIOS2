"""Persistent execution state with process-safe optimistic CAS."""
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
except ImportError:
    fcntl = None

class ExecutionStoreCorruptionError(RuntimeError): pass
class ExecutionVersionConflictError(RuntimeError): pass

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
    def __init__(self, path: Path): self.path, self.handle = path, None
    def __enter__(self):
        self.path.touch(exist_ok=True); self.handle=self.path.open("r+", encoding="utf-8")
        if fcntl is not None: fcntl.flock(self.handle.fileno(), fcntl.LOCK_EX)
        return self
    def __exit__(self, exc_type, exc, tb):
        if fcntl is not None: fcntl.flock(self.handle.fileno(), fcntl.LOCK_UN)
        self.handle.close()

class ExecutionStore:
    def __init__(self, path="data/executions.json", state_machine=None, audit_log=None):
        self.path=Path(path); self.path.parent.mkdir(parents=True, exist_ok=True); self.lock_path=self.path.with_suffix(self.path.suffix+".lock")
        self.state_machine=state_machine or ExecutionStateMachine(); self.audit_log=audit_log
        if not self.path.exists():
            with _FileLock(self.lock_path):
                if not self.path.exists(): self._write({})
    def _read_unlocked(self)->Dict[str,Any]:
        try: data=json.loads(self.path.read_text(encoding="utf-8"))
        except FileNotFoundError: return {}
        except json.JSONDecodeError as exc: raise ExecutionStoreCorruptionError(f"execution store contains invalid JSON: {self.path}") from exc
        if not isinstance(data,dict): raise ExecutionStoreCorruptionError(f"execution store root must be an object: {self.path}")
        return data
    def _write(self,data):
        tmp=self.path.with_suffix(self.path.suffix+".tmp")
        with tmp.open("w",encoding="utf-8") as h:
            json.dump(data,h,ensure_ascii=False,default=str,indent=2); h.flush(); import os; os.fsync(h.fileno())
        tmp.replace(self.path)
    @staticmethod
    def _version(raw):
        if raw is None:return 0
        value=raw.get("version",0)
        if not isinstance(value,int) or value<0: raise ExecutionStoreCorruptionError("execution state has invalid version")
        return value
    def save(self,state): return self._save(state,None)
    def compare_and_set(self,state,expected_version):
        if not isinstance(expected_version,int) or expected_version<0: raise ValueError("expected_version must be a non-negative integer")
        return self._save(state,expected_version)
    def _save(self,state,expected_version):
        if not state.execution_id: raise ValueError("execution_id must be a non-empty string")
        with _FileLock(self.lock_path):
            data=self._read_unlocked(); previous=data.get(state.execution_id); current_version=self._version(previous)
            if expected_version is not None and current_version!=expected_version: raise ExecutionVersionConflictError(f"execution '{state.execution_id}' version changed: expected {expected_version}, found {current_version}")
            if previous: self.state_machine.validate(previous.get("status","pending"),state.status)
            old_status=previous.get("status","pending") if previous else None; state.version=current_version+1; state.updated_at=datetime.now(timezone.utc).isoformat(); data[state.execution_id]=asdict(state); self._write(data)
        if self.audit_log and old_status!=state.status: self.audit_log.append(ExecutionAuditEvent(state.execution_id,old_status or "new",state.status,state.attempt,state.error,correlation_id=state.correlation_id))
        return state
    def transition(self,execution_id,status,**updates):
        state=self.get(execution_id)
        if not state:
            if status!="pending": raise KeyError(execution_id)
            state=ExecutionState(execution_id=execution_id)
        state.status=status
        for key,value in updates.items(): setattr(state,key,value)
        return self.save(state)
    def get(self,execution_id):
        with _FileLock(self.lock_path): raw=self._read_unlocked().get(execution_id)
        return ExecutionState(**raw) if raw else None
    def resumable(self):
        with _FileLock(self.lock_path): values=self._read_unlocked().values()
        return [ExecutionState(**raw) for raw in values if raw.get("status") in {"running","retrying"}]
