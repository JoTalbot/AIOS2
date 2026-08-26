"""Persistent operator queues for quarantine and manual recovery decisions."""
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Optional
@dataclass(frozen=True)
class RecoveryQueueItem:
    execution_id: str; action: str; reason: str; attempt: int; correlation_id: Optional[str]=None; created_at: str=field(default_factory=lambda: datetime.now(timezone.utc).isoformat()); resolved: bool=False
class RecoveryQueue:
    def __init__(self, path: str="data/recovery_queue.jsonl"): self.path=Path(path); self.path.parent.mkdir(parents=True, exist_ok=True)
    def _read(self): return [] if not self.path.exists() else [RecoveryQueueItem(**json.loads(x)) for x in self.path.read_text(encoding="utf-8").splitlines() if x.strip()]
    def _rewrite(self, items):
        tmp=self.path.with_suffix(self.path.suffix+".tmp"); tmp.write_text("".join(json.dumps(asdict(i), ensure_ascii=False)+"\n" for i in items), encoding="utf-8"); tmp.replace(self.path)
    def enqueue(self, item):
        if any(x.execution_id==item.execution_id and x.action==item.action and not x.resolved for x in self._read()): return item
        with self.path.open("a", encoding="utf-8") as h: h.write(json.dumps(asdict(item), ensure_ascii=False)+"\n")
        return item
    def resolve(self, execution_id, action):
        items=self._read(); changed=False; out=[]
        for i in items:
            if i.execution_id==execution_id and i.action==action and not i.resolved: i=RecoveryQueueItem(i.execution_id,i.action,i.reason,i.attempt,i.correlation_id,i.created_at,True); changed=True
            out.append(i)
        if changed: self._rewrite(out)
        return changed
    def items(self, action=None, unresolved_only=False): return [i for i in self._read() if (action is None or i.action==action) and (not unresolved_only or not i.resolved)]
