"""Structured and persistent audit trail for vNext execution lifecycle."""
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import hashlib, json, os
from pathlib import Path
from typing import Any, Dict, List, Optional
try: import fcntl
except ImportError: fcntl = None

@dataclass(frozen=True)
class ExecutionAuditEvent:
    execution_id: str; from_status: str; to_status: str; attempt: int=0; reason: Optional[str]=None; timestamp: str=field(default_factory=lambda: datetime.now(timezone.utc).isoformat()); event_id: str=""; correlation_id: Optional[str]=None
    def with_identity(self):
        if self.event_id:return self
        payload=f"{self.execution_id}|{self.from_status}|{self.to_status}|{self.attempt}|{self.reason}|{self.timestamp}|{self.correlation_id}"
        return ExecutionAuditEvent(**{**asdict(self),"event_id":hashlib.sha256(payload.encode()).hexdigest()})
@dataclass
class AuditEvent:
    event:str; agent_id:str; tool:Optional[str]=None; status:str="ok"; metadata:Dict[str,Any]=field(default_factory=dict); timestamp:str=field(default_factory=lambda: datetime.now(timezone.utc).isoformat()); execution_id:Optional[str]=None; correlation_id:Optional[str]=None
class ExecutionAudit:
    def __init__(self, path: Optional[str]=None): self.events:List[AuditEvent]=[]; self.log=ExecutionAuditLog(path) if path else None
    def record(self,event,agent_id,tool=None,status="ok",context=None,correlation_id=None,**metadata):
        item=AuditEvent(event,agent_id,tool,status,metadata,execution_id=getattr(context,"execution_id",None),correlation_id=correlation_id); self.events.append(item); return item
    def record_event(self,event): return self.record(event.type,event.context.agent_id,context=event.context,**event.data)
    def snapshot(self): return list(self.events)
    def record_transition(self, execution_id, agent_id, from_status, to_status, attempt=0, reason=None, correlation_id=None):
        return self.log.append(ExecutionAuditEvent(execution_id,from_status,to_status,attempt,reason,correlation_id=correlation_id)) if self.log else None
    def load(self, execution_id=None): return self.log.events(execution_id) if self.log else []
class ExecutionAuditLog:
    def __init__(self,path="data/execution_audit.jsonl"):
        self.path=Path(path); self.path.parent.mkdir(parents=True,exist_ok=True); self.lock_path=self.path.with_suffix(self.path.suffix+".lock")
    def _read_events_unlocked(self, execution_id=None):
        if not self.path.exists(): return []
        result=[]
        for line in self.path.read_text(encoding="utf-8").splitlines():
            if not line.strip(): continue
            raw=json.loads(line)
            if execution_id is None or raw.get("execution_id")==execution_id: result.append(ExecutionAuditEvent(**raw))
        return result
    def append(self,event):
        event=event.with_identity(); self.lock_path.touch(exist_ok=True)
        with self.lock_path.open("r+",encoding="utf-8") as lock:
            if fcntl is not None: fcntl.flock(lock.fileno(),fcntl.LOCK_EX)
            try:
                for existing in self._read_events_unlocked():
                    if existing.event_id == event.event_id: return existing
                with self.path.open("a",encoding="utf-8") as h:
                    h.write(json.dumps(asdict(event),ensure_ascii=False)+"\n"); h.flush(); os.fsync(h.fileno())
                return event
            finally:
                if fcntl is not None: fcntl.flock(lock.fileno(),fcntl.LOCK_UN)
    def events(self,execution_id=None):
        self.lock_path.touch(exist_ok=True)
        with self.lock_path.open("r+",encoding="utf-8") as lock:
            if fcntl is not None: fcntl.flock(lock.fileno(),fcntl.LOCK_EX)
            try: return self._read_events_unlocked(execution_id)
            finally:
                if fcntl is not None: fcntl.flock(lock.fileno(),fcntl.LOCK_UN)
