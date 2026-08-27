"""Persistent operator queues for quarantine and manual recovery decisions."""
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Optional

try:
    import fcntl
except ImportError:  # pragma: no cover
    fcntl = None

@dataclass(frozen=True)
class RecoveryQueueItem:
    execution_id: str
    action: str
    reason: str
    attempt: int
    correlation_id: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    resolved: bool = False

class _QueueLock:
    def __init__(self, path):
        self.path=path; self.handle=None
    def __enter__(self):
        self.path.touch(exist_ok=True); self.handle=self.path.open("r+", encoding="utf-8")
        if fcntl is not None: fcntl.flock(self.handle.fileno(), fcntl.LOCK_EX)
        return self
    def __exit__(self,*args):
        if fcntl is not None: fcntl.flock(self.handle.fileno(), fcntl.LOCK_UN)
        self.handle.close()

class RecoveryQueue:
    def __init__(self, path: str="data/recovery_queue.jsonl"):
        self.path=Path(path); self.path.parent.mkdir(parents=True, exist_ok=True); self.lock_path=self.path.with_suffix(self.path.suffix+".lock")
    def _read_unlocked(self):
        return [] if not self.path.exists() else [RecoveryQueueItem(**json.loads(x)) for x in self.path.read_text(encoding="utf-8").splitlines() if x.strip()]
    def _rewrite_unlocked(self, items):
        tmp=self.path.with_suffix(self.path.suffix+".tmp")
        tmp.write_text("".join(json.dumps(asdict(i), ensure_ascii=False)+"\n" for i in items), encoding="utf-8")
        with tmp.open("r+", encoding="utf-8") as h:
            h.flush(); import os; os.fsync(h.fileno())
        tmp.replace(self.path)
    def enqueue(self,item):
        with _QueueLock(self.lock_path):
            items=self._read_unlocked()
            if any(x.execution_id==item.execution_id and x.action==item.action and not x.resolved for x in items): return item
            with self.path.open("a",encoding="utf-8") as h:
                h.write(json.dumps(asdict(item),ensure_ascii=False)+"\n"); h.flush(); import os; os.fsync(h.fileno())
            return item
    def resolve(self,execution_id,action):
        with _QueueLock(self.lock_path):
            items=self._read_unlocked(); changed=False; out=[]
            for i in items:
                if i.execution_id==execution_id and i.action==action and not i.resolved:
                    i=RecoveryQueueItem(i.execution_id,i.action,i.reason,i.attempt,i.correlation_id,i.created_at,True); changed=True
                out.append(i)
            if changed: self._rewrite_unlocked(out)
            return changed
    def items(self,action=None,unresolved_only=False):
        with _QueueLock(self.lock_path):
            return [i for i in self._read_unlocked() if (action is None or i.action==action) and (not unresolved_only or not i.resolved)]
