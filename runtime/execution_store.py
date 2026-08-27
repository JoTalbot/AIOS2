"""Persistent execution state with process-safe optimistic CAS."""
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import json, os
from pathlib import Path
from typing import Any, Optional
from .execution_audit import ExecutionAuditEvent
from .execution_context import ExecutionContext
from .execution_state_machine import ExecutionStateMachine
from .tool_protocol import ToolResult
try: import fcntl
except ImportError: fcntl=None
class ExecutionStoreCorruptionError(RuntimeError): pass
class ExecutionVersionConflictError(RuntimeError): pass
class ExecutionFencingConflictError(RuntimeError): pass
@dataclass
class ExecutionState:
    execution_id: str; status: str="pending"; goal: str=""; attempt: int=0; plan: Any=None; result: Any=None; error: Optional[str]=None; updated_at: str=field(default_factory=lambda:datetime.now(timezone.utc).isoformat()); correlation_id: Optional[str]=None; version: int=0
class _FileLock:
    def __init__(self,path): self.path,self.handle=Path(path),None
    def __enter__(self):
        self.path.parent.mkdir(parents=True,exist_ok=True); self.path.touch(exist_ok=True); self.handle=self.path.open("r+",encoding="utf-8")
        if fcntl is not None: fcntl.flock(self.handle.fileno(),fcntl.LOCK_EX)
        return self
    def __exit__(self,exc_type,exc,tb):
        if fcntl is not None: fcntl.flock(self.handle.fileno(),fcntl.LOCK_UN)
        self.handle.close()
class ExecutionStore:
    def __init__(self,path="data/executions.json",state_machine=None,audit_log=None,coordination_lock_path=None):
        self.path=Path(path); self.path.parent.mkdir(parents=True,exist_ok=True); self.lock_path=self.path.with_suffix(self.path.suffix+".lock"); self.coordination_lock_path=Path(coordination_lock_path) if coordination_lock_path else None; self.state_machine=state_machine or ExecutionStateMachine(); self.audit_log=audit_log
        if not self.path.exists():
            with _FileLock(self.lock_path):
                if not self.path.exists(): self._write({})
    def execution_lock(self): return _FileLock(self.coordination_lock_path or self.lock_path)
    def _read_unlocked(self):
        try: data=json.loads(self.path.read_text(encoding="utf-8"))
        except FileNotFoundError:return {}
        except json.JSONDecodeError as exc:raise ExecutionStoreCorruptionError(f"execution store contains invalid JSON: {self.path}") from exc
        if not isinstance(data,dict):raise ExecutionStoreCorruptionError(f"execution store root must be an object: {self.path}")
        return data
    def _write(self,data):
        tmp=self.path.with_suffix(self.path.suffix+".tmp")
        try:
            with tmp.open("w",encoding="utf-8") as h:json.dump(data,h,ensure_ascii=False,default=str,indent=2);h.flush();os.fsync(h.fileno())
            tmp.replace(self.path)
        finally:
            if tmp.exists():
                try:tmp.unlink()
                except OSError:pass
    @staticmethod
    def _version(raw):
        if raw is None:return 0
        value=raw.get("version",0)
        if not isinstance(value,int) or value<0:raise ExecutionStoreCorruptionError("execution state has invalid version")
        return value
    @staticmethod
    def _decode_value(value):
        if isinstance(value,list):return [ExecutionStore._decode_value(x) for x in value]
        if isinstance(value,dict):
            if {"call_id","tool","ok"}.issubset(value):
                try:return ToolResult(value["call_id"],value["tool"],bool(value["ok"]),ExecutionStore._decode_value(value.get("value")),value.get("error"),bool(value.get("retryable",False)),value.get("idempotency_key"))
                except Exception:pass
            return {k:ExecutionStore._decode_value(v) for k,v in value.items()}
        return value
    def save(self,state):return self._save(state,None,validate_transition=False)
    def compare_and_set(self,state,expected_version,*,expected_status=None,fencing_token=None,fencing_validator=None,lock_held=False):
        if not isinstance(expected_version,int) or expected_version<0:raise ValueError("expected_version must be a non-negative integer")
        if lock_held:return self._save_unlocked(state,expected_version,True,expected_status=expected_status,fencing_token=fencing_token,fencing_validator=fencing_validator)
        return self._save(state,expected_version,True,expected_status=expected_status,fencing_token=fencing_token,fencing_validator=fencing_validator)
    def _save(self,state,expected_version,validate_transition=True,**kwargs):
        with _FileLock(self.lock_path):return self._save_unlocked(state,expected_version,validate_transition,**kwargs)
    def _save_unlocked(self,state,expected_version,validate_transition=True,*,expected_status=None,fencing_token=None,fencing_validator=None):
        if not state.execution_id:raise ValueError("execution_id must be a non-empty string")
        data=self._read_unlocked(); previous=data.get(state.execution_id); current_version=self._version(previous)
        if expected_version is not None and current_version!=expected_version:raise ExecutionVersionConflictError(f"execution '{state.execution_id}' version changed")
        if expected_status is not None and (previous or {}).get("status","pending")!=expected_status:raise ExecutionVersionConflictError(f"execution '{state.execution_id}' status changed")
        if fencing_validator is not None and not fencing_validator(state.execution_id,fencing_token):raise ExecutionFencingConflictError(f"execution '{state.execution_id}' fencing token is stale")
        if previous and validate_transition:self.state_machine.validate(previous.get("status","pending"),state.status)
        old_status=previous.get("status","pending") if previous else None; state.version=current_version+1; state.updated_at=datetime.now(timezone.utc).isoformat(); data[state.execution_id]=asdict(state); self._write(data)
        if self.audit_log and old_status!=state.status:self.audit_log.append(ExecutionAuditEvent(state.execution_id,old_status or "new",state.status,state.attempt,state.error,correlation_id=state.correlation_id))
        return state
    def transition(self,execution_id,status,**updates):
        state=self.get(execution_id)
        if not state:
            if status!="pending":raise KeyError(execution_id)
            state=ExecutionState(execution_id=execution_id)
        state.status=status
        for key,value in updates.items():setattr(state,key,value)
        return self.compare_and_set(state,state.version)
    def get(self,execution_id):
        with _FileLock(self.lock_path):raw=self._read_unlocked().get(execution_id)
        if not raw:return None
        raw=dict(raw);raw["result"]=self._decode_value(raw.get("result"));return ExecutionState(**raw)
    def resumable(self):
        with _FileLock(self.lock_path):values=list(self._read_unlocked().values())
        return [ExecutionState(**{**raw,"result":self._decode_value(raw.get("result"))}) for raw in values if raw.get("status") in {"running","retrying"} or (raw.get("status")=="pending" and raw.get("attempt",0)>0)]
