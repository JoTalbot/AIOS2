"""Crash-recoverable execution commit protocol with an integrity-protected journal."""
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import hashlib, json, os
from pathlib import Path
from typing import Any, Optional
from .execution_audit import ExecutionAuditEvent, ExecutionAuditLog
from .execution_store import ExecutionFencingConflictError, ExecutionState, ExecutionStore, ExecutionVersionConflictError
try: import fcntl
except ImportError: fcntl=None
@dataclass(frozen=True)
class ExecutionCommit:
    commit_id:str; execution_id:str; from_status:str; to_status:str; attempt:int; checkpoint:Any=None; reason:Optional[str]=None; created_at:str=field(default_factory=lambda:datetime.now(timezone.utc).isoformat()); correlation_id:Optional[str]=None; status:str="pending"; sequence:int=0; checksum:str=""
    def with_integrity(self):
        if self.checksum:return self
        payload=asdict(self); payload.pop("checksum",None); raw=json.dumps(payload,ensure_ascii=False,sort_keys=True,default=str); return ExecutionCommit(**{**payload,"checksum":hashlib.sha256(raw.encode()).hexdigest()})
class CorruptJournalError(ValueError): pass
class _JournalLock:
    def __init__(self,path):self.path,self.handle=Path(path),None
    def __enter__(self):
        self.path.touch(exist_ok=True);self.handle=self.path.open("r+",encoding="utf-8")
        if fcntl is not None:fcntl.flock(self.handle.fileno(),fcntl.LOCK_EX)
        return self
    def __exit__(self,*args):
        if fcntl is not None:fcntl.flock(self.handle.fileno(),fcntl.LOCK_UN)
        self.handle.close()
class ExecutionCommitCoordinator:
    def __init__(self,store,audit_log,journal_path="data/execution_commits.jsonl",quarantine_path="data/execution_commits.quarantine.jsonl",lease_store=None,lease_owner_id=None,fencing_token=None):
        self.store=store;self.audit_log=audit_log;self.journal_path=Path(journal_path);self.quarantine_path=Path(quarantine_path);self.lease_store=lease_store;self.lease_owner_id=lease_owner_id;self.fencing_token=fencing_token;self.journal_path.parent.mkdir(parents=True,exist_ok=True);self.lock_path=self.journal_path.with_suffix(self.journal_path.suffix+".lock")
        if self.lease_store is not None:self.lease_store.lock_path=self.store.coordination_lock_path or self.store.lock_path
    def _next_sequence_unlocked(self):
        if not self.journal_path.exists():return 1
        maximum=0
        for line in self.journal_path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                try:maximum=max(maximum,int(json.loads(line).get("sequence",0)))
                except (json.JSONDecodeError,TypeError,ValueError,AttributeError):pass
        return maximum+1
    def _append_journal(self,commit):
        with _JournalLock(self.lock_path):
            commit=ExecutionCommit(**{**asdict(commit),"sequence":self._next_sequence_unlocked()}).with_integrity()
            with self.journal_path.open("a",encoding="utf-8") as h:h.write(json.dumps(asdict(commit),ensure_ascii=False,default=str)+"\n");h.flush();os.fsync(h.fileno())
            return commit
    def _read_journal_unlocked(self):
        if not self.journal_path.exists():return []
        result=[];expected=1
        for line in self.journal_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():continue
            raw={}
            try:
                raw=json.loads(line);sequence=int(raw.get("sequence",expected));raw.setdefault("status","pending");raw.setdefault("sequence",sequence);commit=ExecutionCommit(**raw)
                if commit.sequence!=expected or commit.with_integrity().checksum!=commit.checksum:raise CorruptJournalError(f"invalid journal integrity at sequence {expected}")
            except (json.JSONDecodeError,TypeError,KeyError,ValueError,CorruptJournalError) as exc:
                self._quarantine(line,str(exc));expected=max(expected+1,int(raw.get("sequence",0))+1) if isinstance(raw,dict) else expected+1;continue
            result.append(commit);expected=commit.sequence+1
        return result
    def _read_journal(self):
        with _JournalLock(self.lock_path):return self._read_journal_unlocked()
    def _quarantine(self,line,reason):
        self.quarantine_path.parent.mkdir(parents=True,exist_ok=True)
        if self.quarantine_path.exists():
            for existing in self.quarantine_path.read_text(encoding="utf-8").splitlines():
                try:
                    record=json.loads(existing)
                    if record.get("line")==line and record.get("reason")==reason:return
                except (json.JSONDecodeError,TypeError):
                    continue
        with self.quarantine_path.open("a",encoding="utf-8") as h:
            h.write(json.dumps({"reason":reason,"line":line,"quarantined_at":datetime.now(timezone.utc).isoformat()},ensure_ascii=False)+"\n");h.flush();os.fsync(h.fileno())
    def _lease_valid_unlocked(self,execution_id):
        if self.lease_store is None:return True
        if not self.lease_owner_id or self.fencing_token is None:return False
        checker=getattr(self.lease_store,"is_owner_unlocked",None)
        return checker(execution_id,self.lease_owner_id,self.fencing_token) if checker else self.lease_store.is_owner(execution_id,self.lease_owner_id,self.fencing_token)
    def _fencing_validator(self,execution_id,token):return token==self.fencing_token and self._lease_valid_unlocked(execution_id)
    def _next_state(self,state,status,checkpoint=None,reason=None):return ExecutionState(**{**asdict(state),"status":status,"result":checkpoint if status=="completed" else state.result,"error":reason if status=="failed" else state.error})
    def commit(self,state,to_status,*,checkpoint=None,reason=None):
        commit_id=f"{state.execution_id}:{state.attempt}:{to_status}:{state.correlation_id or ''}"
        existing={c.commit_id:c for c in self.pending(all_statuses=True)}.get(commit_id)
        if existing:return existing
        commit=self._append_journal(ExecutionCommit(commit_id,state.execution_id,state.status,to_status,state.attempt,checkpoint,reason,correlation_id=state.correlation_id))
        with self.store.execution_lock():
            current=self.store._get_unlocked(state.execution_id) if hasattr(self.store,"_get_unlocked") else self.store.get(state.execution_id)
            if not current or not self._lease_valid_unlocked(current.execution_id):return commit
            try:self.store.compare_and_set(self._next_state(current,to_status,checkpoint,reason),current.version,expected_status=current.status,fencing_token=self.fencing_token,fencing_validator=self._fencing_validator,lock_held=True)
            except (ExecutionFencingConflictError,ExecutionVersionConflictError,PermissionError):return commit
            self.audit_log.append(ExecutionAuditEvent(current.execution_id,current.status,to_status,current.attempt,reason,correlation_id=current.correlation_id,event_id=commit_id));self._mark(commit_id,"applied")
        return commit
    def _mark(self,commit_id,status):
        with _JournalLock(self.lock_path):
            commits=self._read_journal_unlocked()
            for i,commit in enumerate(commits):
                if commit.commit_id==commit_id:commits[i]=ExecutionCommit(**{**asdict(commit),"status":status}).with_integrity();break
            tmp=self.journal_path.with_suffix(self.journal_path.suffix+".tmp");tmp.write_text("".join(json.dumps(asdict(c.with_integrity()),ensure_ascii=False,default=str)+"\n" for c in commits),encoding="utf-8")
            with tmp.open("r+",encoding="utf-8") as h:h.flush();os.fsync(h.fileno())
            tmp.replace(self.journal_path)
            if hasattr(os,"O_DIRECTORY"):
                try:
                    fd=os.open(str(self.journal_path.parent),os.O_RDONLY|os.O_DIRECTORY);os.fsync(fd);os.close(fd)
                except OSError:pass
    def reconcile(self):
        repaired=[]
        for commit in self.pending():
            with self.store.execution_lock():
                state=self.store._get_unlocked(commit.execution_id) if hasattr(self.store,"_get_unlocked") else self.store.get(commit.execution_id)
                if not state or not self._lease_valid_unlocked(commit.execution_id):continue
                if state.status==commit.to_status:
                    self.audit_log.append(ExecutionAuditEvent(commit.execution_id,commit.from_status,commit.to_status,commit.attempt,commit.reason,correlation_id=commit.correlation_id,event_id=commit.commit_id));self._mark(commit.commit_id,"reconciled");repaired.append(commit.commit_id);continue
                if state.status!=commit.from_status:continue
                try:self.store.compare_and_set(self._next_state(state,commit.to_status,commit.checkpoint,commit.reason),state.version,expected_status=commit.from_status,fencing_token=self.fencing_token,fencing_validator=self._fencing_validator,lock_held=True)
                except (ExecutionFencingConflictError,ExecutionVersionConflictError,PermissionError):continue
                self.audit_log.append(ExecutionAuditEvent(commit.execution_id,commit.from_status,commit.to_status,commit.attempt,commit.reason,correlation_id=commit.correlation_id,event_id=commit.commit_id));self._mark(commit.commit_id,"reconciled");repaired.append(commit.commit_id)
        return repaired
    def pending(self,all_statuses=False):
        commits=self._read_journal();return commits if all_statuses else [c for c in commits if c.status=="pending"]