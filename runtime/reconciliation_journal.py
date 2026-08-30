"""Durable, idempotent journal for recovery reconciliation intents."""
from .paths import data_path
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
import json, os
from pathlib import Path
from typing import Optional
try: import fcntl
except ImportError: fcntl = None

SCHEMA_VERSION = 1

@dataclass(frozen=True)
class ReconciliationRecord:
    intent_key: str
    execution_id: Optional[str]
    status: str = "pending"
    result: object = None
    updated_at: str = ""
    schema_version: int = SCHEMA_VERSION

class ReconciliationJournal:
    def __init__(self, path=None):
        path = path or data_path("reconciliation_journal.json")
        self.path=Path(path); self.path.parent.mkdir(parents=True,exist_ok=True); self.lock_path=self.path.with_suffix(self.path.suffix+".lock")
        if not self.path.exists():
            with self._lock():
                if not self.path.exists(): self._write({})
    def _lock(self):
        class Lock:
            def __enter__(s):
                self.lock_path.touch(exist_ok=True); s.h=self.lock_path.open("r+")
                if fcntl: fcntl.flock(s.h.fileno(),fcntl.LOCK_EX)
                return s
            def __exit__(s,*a):
                if fcntl: fcntl.flock(s.h.fileno(),fcntl.LOCK_UN)
                s.h.close()
        return Lock()
    def _read(self):
        try:return json.loads(self.path.read_text(encoding="utf-8"))
        except FileNotFoundError:return {}
    def _write(self,data):
        tmp=self.path.with_suffix(self.path.suffix+".tmp")
        tmp.write_text(json.dumps(data,ensure_ascii=False,sort_keys=True,indent=2),encoding="utf-8")
        with tmp.open("r+") as h:h.flush();os.fsync(h.fileno())
        tmp.replace(self.path)
    @staticmethod
    def _record(intent_key, raw):
        if not isinstance(raw, dict): raise ValueError("invalid journal record")
        if raw.get("intent_key") != intent_key or "execution_id" not in raw or "status" not in raw:
            raise ValueError("invalid journal record")
        version=raw.get("schema_version", SCHEMA_VERSION)
        if not isinstance(version, int) or isinstance(version, bool) or version < 1:
            raise ValueError("invalid journal schema version")
        if version > SCHEMA_VERSION:
            raise ValueError("unsupported journal schema version")
        migrated=dict(raw)
        migrated["schema_version"]=SCHEMA_VERSION
        return ReconciliationRecord(**migrated)
    def get(self,intent_key):
        with self._lock():
            raw=self._read().get(intent_key); return self._record(intent_key, raw) if raw else None
    def begin(self,intent_key,execution_id=None):
        with self._lock():
            data=self._read(); raw=data.get(intent_key)
            if raw:return self._record(intent_key, raw)
            record=ReconciliationRecord(intent_key,execution_id,"pending",None,datetime.now(timezone.utc).isoformat()); data[intent_key]=asdict(record); self._write(data); return record
    def complete(self,intent_key,result): return self._set(intent_key,"completed",result)
    def fail(self,intent_key,result=None): return self._set(intent_key,"failed",result)
    def _set(self,intent_key,status,result):
        with self._lock():
            data=self._read(); raw=data.get(intent_key)
            if raw and raw.get("status") in {"completed","failed"}:return self._record(intent_key, raw)
            record=ReconciliationRecord(intent_key,raw.get("execution_id") if raw else None,status,result,datetime.now(timezone.utc).isoformat()); data[intent_key]=asdict(record); self._write(data); return record
    def pending(self):
        with self._lock():
            return [self._record(k,r) for k,r in self._read().items() if r.get("status")=="pending"]
    def compact(self, retention=timedelta(days=30), now=None):
        """Remove only terminal records older than retention; pending records are never removed."""
        cutoff=(now or datetime.now(timezone.utc))-retention
        with self._lock():
            data=self._read(); removed=0
            for key, raw in list(data.items()):
                if raw.get("status") not in {"completed","failed"}: continue
                try: updated=datetime.fromisoformat(raw.get("updated_at", ""))
                except (TypeError, ValueError): continue
                if updated.tzinfo is None: updated=updated.replace(tzinfo=timezone.utc)
                if updated < cutoff: del data[key]; removed += 1
            if removed: self._write(data)
            return removed
