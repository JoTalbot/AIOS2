"""Durable intent ledger for side-effecting tool calls."""
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
from typing import Any, Optional
try:
    import fcntl
except ImportError:  # pragma: no cover
    fcntl = None
AMBIGUOUS_STATES = frozenset({"prepared", "executing", "ambiguous"})
VALID_STATES = AMBIGUOUS_STATES | {"completed", "failed"}
@dataclass(frozen=True)
class ToolIntent:
    idempotency_key: str
    call_id: str
    tool: str
    arguments: Any = field(default_factory=dict)
    execution_id: Optional[str] = None
    state: str = "prepared"
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    owner_id: Optional[str] = None
    claim_token: Optional[str] = None
    claim_expires_at: Optional[str] = None
class _IntentLock:
    def __init__(self,path:Path): self.path,self.handle=path,None
    def __enter__(self):
        self.path.touch(exist_ok=True); self.handle=self.path.open("r+",encoding="utf-8")
        if fcntl is not None: fcntl.flock(self.handle.fileno(),fcntl.LOCK_EX)
        return self
    def __exit__(self,*args):
        if fcntl is not None: fcntl.flock(self.handle.fileno(),fcntl.LOCK_UN)
        self.handle.close()
class ToolIntentStore:
    def __init__(self,path="data/tool_intents.json",claim_ttl_seconds=60):
        self.path=Path(path); self.path.parent.mkdir(parents=True,exist_ok=True); self.lock_path=self.path.with_suffix(self.path.suffix+".lock"); self.claim_ttl_seconds=max(1,claim_ttl_seconds)
    def _read(self):
        if not self.path.exists(): return {}
        data=json.loads(self.path.read_text(encoding="utf-8"));
        if not isinstance(data,dict): raise ValueError("tool intent store must be an object")
        return data
    def get(self,key):
        if not key:return None
        with _IntentLock(self.lock_path): raw=self._read().get(key)
        return ToolIntent(**raw) if raw else None
    def prepare(self,intent):
        if intent.state not in VALID_STATES: raise ValueError("invalid intent state")
        with _IntentLock(self.lock_path):
            data=self._read(); raw=data.get(intent.idempotency_key)
            if raw:return ToolIntent(**raw)
            data[intent.idempotency_key]=asdict(intent); self._write(data); return intent
    def claim(self,key,owner_id,claim_token):
        if not key or not owner_id or not claim_token: raise ValueError("key, owner_id and claim_token are required")
        now=datetime.now(timezone.utc)
        with _IntentLock(self.lock_path):
            data=self._read(); raw=data.get(key)
            if raw is None or raw.get("state") not in AMBIGUOUS_STATES:return None
            expiry=raw.get("claim_expires_at")
            if raw.get("owner_id") not in (None,owner_id) and expiry and datetime.fromisoformat(expiry)>now:return None
            if raw.get("owner_id")==owner_id and raw.get("claim_token") not in (None,claim_token):return None
            raw["owner_id"],raw["claim_token"],raw["claim_expires_at"],raw["state"]=owner_id,claim_token,(now+timedelta(seconds=self.claim_ttl_seconds)).isoformat(),"executing"
            self._write(data); return ToolIntent(**raw)
    def renew_claim(self,key,owner_id,claim_token):
        now=datetime.now(timezone.utc)
        with _IntentLock(self.lock_path):
            data=self._read(); raw=data.get(key)
            if raw is None or raw.get("state") not in AMBIGUOUS_STATES or raw.get("owner_id")!=owner_id or raw.get("claim_token")!=claim_token:return False
            expiry=raw.get("claim_expires_at")
            if not expiry or datetime.fromisoformat(expiry)<=now:return False
            raw["claim_expires_at"]=(now+timedelta(seconds=self.claim_ttl_seconds)).isoformat(); self._write(data); return True
    def release_claim(self,key,owner_id,claim_token,state="ambiguous"):
        if state not in AMBIGUOUS_STATES:raise ValueError("release state must be ambiguous")
        with _IntentLock(self.lock_path):
            data=self._read(); raw=data.get(key)
            if raw is None or raw.get("owner_id")!=owner_id or raw.get("claim_token")!=claim_token:return False
            raw["owner_id"],raw["claim_token"],raw["claim_expires_at"],raw["state"]=None,None,None,state; self._write(data); return True
    def mark_claimed(self,key,owner_id,claim_token,state):
        if state not in VALID_STATES or state in AMBIGUOUS_STATES:raise ValueError("mark_claimed requires a terminal state")
        with _IntentLock(self.lock_path):
            data=self._read(); raw=data.get(key)
            if raw is None or raw.get("owner_id")!=owner_id or raw.get("claim_token")!=claim_token:return None
            expiry=raw.get("claim_expires_at")
            if not expiry or datetime.fromisoformat(expiry)<=datetime.now(timezone.utc):return None
            raw["state"],raw["owner_id"],raw["claim_token"],raw["claim_expires_at"]=state,None,None,None; self._write(data); return ToolIntent(**raw)
    def mark(self,key,state):
        if state not in {"completed","failed"}: raise ValueError("mark requires a terminal state")
        with _IntentLock(self.lock_path):
            data=self._read(); raw=data.get(key)
            if raw is None:return None
            if raw.get("owner_id") is not None:return None
            if raw.get("state") in {"completed","failed"}: return ToolIntent(**raw)
            raw["state"]=state; self._write(data); return ToolIntent(**raw)
    def pending(self):
        with _IntentLock(self.lock_path):return [ToolIntent(**raw) for raw in self._read().values() if raw.get("state") in AMBIGUOUS_STATES]
    def _write(self,data):
        tmp=self.path.with_suffix(self.suffix if hasattr(self,"suffix") else self.path.suffix+".tmp")
        tmp.write_text(json.dumps(data,ensure_ascii=False,default=str,indent=2),encoding="utf-8")
        with tmp.open("r+",encoding="utf-8") as h:h.flush(); import os; os.fsync(h.fileno())
        tmp.replace(self.path)
