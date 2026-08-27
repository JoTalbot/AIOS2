"""Crash-recoverable canonical execution commit protocol."""

from contextlib import contextmanager
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any, Optional

from .execution_audit import ExecutionAuditEvent, ExecutionAuditLog
from .execution_store import ExecutionConcurrencyError, ExecutionState, ExecutionStore

try:
    import fcntl
except ImportError:
    fcntl = None

@dataclass(frozen=True)
class ExecutionCommit:
    commit_id: str
    execution_id: str
    from_status: str
    to_status: str
    attempt: int
    checkpoint: Any = None
    reason: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    correlation_id: Optional[str] = None
    status: str = "pending"
    sequence: int = 0
    checksum: str = ""
    expected_version: Optional[int] = None
    fencing_token: Optional[int] = None
    def with_integrity(self):
        payload = asdict(self); payload.pop("checksum", None)
        raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str)
        return ExecutionCommit(**{**payload, "checksum": hashlib.sha256(raw.encode()).hexdigest()})

class CorruptJournalError(ValueError):
    pass

class ReconcileResult(list):
    """Compatibility result: iterable repaired commit ids, numerically comparable as a count."""
    def __eq__(self, other):
        if isinstance(other, int):
            return len(self) == other
        return super().__eq__(other)
    def __int__(self):
        return len(self)

class ExecutionCommitCoordinator:
    """The single lifecycle mutation boundary for durable executions."""
    def __init__(self, store: ExecutionStore, audit_log: Optional[ExecutionAuditLog] = None, journal_path: str = "data/execution_commits.jsonl", quarantine_path: str = "data/execution_commits.quarantine.jsonl"):
        self.store = store; self.audit_log = audit_log or ExecutionAuditLog(); self.journal_path = Path(journal_path); self.quarantine_path = Path(quarantine_path); self.lock_path = self.journal_path.with_suffix(self.journal_path.suffix + ".lock"); self.journal_path.parent.mkdir(parents=True, exist_ok=True)
    @contextmanager
    def _lock(self):
        with self.lock_path.open("a+", encoding="utf-8") as handle:
            if fcntl is not None: fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
            try: yield
            finally:
                if fcntl is not None: fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
    def _max_sequence_unlocked(self):
        if not self.journal_path.exists(): return 0
        maximum = 0
        for line in self.journal_path.read_text(encoding="utf-8").splitlines():
            if not line.strip(): continue
            try: sequence = json.loads(line).get("sequence")
            except json.JSONDecodeError: continue
            if isinstance(sequence, int): maximum = max(maximum, sequence)
        return maximum
    def _append_journal_unlocked(self, commit):
        commit = ExecutionCommit(**{**asdict(commit), "sequence": self._max_sequence_unlocked() + 1}).with_integrity()
        with self.journal_path.open("a", encoding="utf-8") as handle: handle.write(json.dumps(asdict(commit), ensure_ascii=False, default=str) + "\n"); handle.flush()
        return commit
    def _append_journal(self, commit):
        with self._lock(): return self._append_journal_unlocked(commit)
    def _rewrite_unlocked(self, commits):
        tmp = self.journal_path.with_suffix(self.journal_path.suffix + ".tmp"); tmp.write_text("".join(json.dumps(asdict(c.with_integrity()), ensure_ascii=False, default=str) + "\n" for c in commits), encoding="utf-8"); tmp.replace(self.journal_path)
    def _read_journal_unlocked(self):
        if not self.journal_path.exists(): return []
        result=[]; previous_sequence=0
        for line in self.journal_path.read_text(encoding="utf-8").splitlines():
            if not line.strip(): continue
            try:
                raw=json.loads(line); raw.setdefault("status","pending"); raw.setdefault("sequence",previous_sequence+1); raw.setdefault("expected_version",None); raw.setdefault("fencing_token",None); commit=ExecutionCommit(**raw)
                if commit.sequence <= previous_sequence or commit.with_integrity().checksum != commit.checksum: raise CorruptJournalError(f"invalid journal integrity at sequence {commit.sequence}")
            except (json.JSONDecodeError,TypeError,KeyError,CorruptJournalError) as exc:
                self._quarantine(line,str(exc)); continue
            result.append(commit); previous_sequence=commit.sequence
        return result
    def _quarantine(self,line,reason):
        with self.quarantine_path.open("a",encoding="utf-8") as handle: handle.write(json.dumps({"reason":reason,"line":line,"quarantined_at":datetime.now(timezone.utc).isoformat()},ensure_ascii=False)+"\n")
    def commit(self,state,to_status,*,checkpoint=None,reason=None,updates=None,fencing_token=None,correlation_id=None):
        execution_id=state if isinstance(state,str) else state.execution_id; current=self.store.get(execution_id)
        if current is None: current=self.store.create(execution_id) if isinstance(state,str) else self.store.create(execution_id,metadata={"goal":state.goal,"attempt":state.attempt,"plan":state.plan,"correlation_id":state.correlation_id,"fencing_token":state.fencing_token})
        updates=dict(updates or {})
        if to_status=="completed" and checkpoint is not None: updates.setdefault("result",checkpoint)
        if to_status=="failed" and reason is not None: updates.setdefault("error",reason)
        effective_fence=fencing_token if fencing_token is not None else current.fencing_token; effective_correlation=correlation_id if correlation_id is not None else current.correlation_id
        with self._lock():
            commits=self._read_journal_unlocked()
            if current.status==to_status and current.version>0:
                for existing in reversed(commits):
                    if existing.execution_id==current.execution_id and existing.to_status==to_status and existing.expected_version==current.version-1 and existing.fencing_token==effective_fence: return existing
            expected_version=current.version; commit_id=f"{current.execution_id}:{current.attempt}:{current.status}:{to_status}:{expected_version}:{effective_fence}:{effective_correlation or ''}"
            for existing in commits:
                if existing.commit_id==commit_id: return existing
            commit=self._append_journal_unlocked(ExecutionCommit(commit_id,current.execution_id,current.status,to_status,current.attempt,checkpoint,reason,correlation_id=effective_correlation,expected_version=expected_version,fencing_token=effective_fence))
            updated=self.store.transition(current.execution_id,to_status,_audit=False,expected_version=expected_version,fencing_token=effective_fence,**updates)
            self.audit_log.append(ExecutionAuditEvent(current.execution_id,current.status,to_status,current.attempt,reason,correlation_id=effective_correlation,event_id=commit_id,version=updated.version))
            return self._mark_unlocked(commit_id,"applied")
    def _mark_unlocked(self,commit_id,status):
        commits=self._read_journal_unlocked(); result=None
        for i,commit in enumerate(commits):
            if commit.commit_id==commit_id: result=ExecutionCommit(**{**asdict(commit),"status":status}).with_integrity(); commits[i]=result; break
        self._rewrite_unlocked(commits); return result
    def reconcile(self):
        repaired=ReconcileResult()
        with self._lock():
            for commit in [c for c in self._read_journal_unlocked() if c.status=="pending"]:
                state=self.store.get(commit.execution_id)
                if not state: continue
                if state.status==commit.to_status and state.version>(commit.expected_version or -1):
                    self.audit_log.append(ExecutionAuditEvent(commit.execution_id,commit.from_status,commit.to_status,commit.attempt,commit.reason,correlation_id=commit.correlation_id,event_id=commit.commit_id,version=state.version)); self._mark_unlocked(commit.commit_id,"reconciled"); repaired.append(commit.commit_id); continue
                if state.status!=commit.from_status or state.version!=(commit.expected_version or state.version): continue
                updates={"result":commit.checkpoint,"error":None} if commit.to_status=="completed" else ({"error":commit.reason} if commit.to_status=="failed" else {})
                try: updated=self.store.transition(commit.execution_id,commit.to_status,_audit=False,expected_version=commit.expected_version,fencing_token=commit.fencing_token,**updates)
                except ExecutionConcurrencyError: continue
                self.audit_log.append(ExecutionAuditEvent(commit.execution_id,commit.from_status,commit.to_status,commit.attempt,commit.reason,correlation_id=commit.correlation_id,event_id=commit.commit_id,version=updated.version)); self._mark_unlocked(commit.commit_id,"reconciled"); repaired.append(commit.commit_id)
        return repaired
    def pending(self,all_statuses=False):
        commits=self._read_journal(); return commits if all_statuses else [c for c in commits if c.status=="pending"]
    def _read_journal(self):
        with self._lock(): return self._read_journal_unlocked()
