"""Atomic file-backed execution lease with fencing tokens."""
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
from typing import Optional

try:
    import fcntl
except ImportError:  # pragma: no cover
    fcntl = None

@dataclass(frozen=True)
class ExecutionLease:
    execution_id: str
    owner_id: str
    expires_at: str
    fencing_token: int = 0

class LeaseCorruptionError(RuntimeError):
    """Raised when the lease store cannot be trusted."""

class ExecutionLeaseStore:
    def __init__(self, path: str = "data/execution_leases.json", ttl_seconds: int = 60):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.ttl_seconds = max(1, ttl_seconds)
        self.lock_path = self.path.with_suffix(self.path.suffix + ".lock")
        if not self.path.exists():
            with self._lock():
                if not self.path.exists(): self._write({})

    class _Lock:
        def __init__(self, path): self.path, self.handle = path, None
        def __enter__(self):
            self.path.touch(exist_ok=True); self.handle = self.path.open("r+", encoding="utf-8")
            if fcntl is not None: fcntl.flock(self.handle.fileno(), fcntl.LOCK_EX)
            return self
        def __exit__(self, exc_type, exc, tb):
            if fcntl is not None: fcntl.flock(self.handle.fileno(), fcntl.LOCK_UN)
            self.handle.close()

    def _lock(self): return self._Lock(self.lock_path)

    def _read(self):
        try: data = json.loads(self.path.read_text(encoding="utf-8"))
        except (FileNotFoundError, json.JSONDecodeError) as exc: raise LeaseCorruptionError(f"invalid execution lease store: {self.path}") from exc
        if not isinstance(data, dict): raise LeaseCorruptionError("execution lease store must contain an object")
        for execution_id, lease in data.items():
            if not isinstance(execution_id, str) or not isinstance(lease, dict): raise LeaseCorruptionError("execution lease entry has invalid shape")
            if not isinstance(lease.get("owner_id"), str) or not isinstance(lease.get("expires_at"), str): raise LeaseCorruptionError("execution lease entry has invalid owner or expiry")
            if not isinstance(lease.get("fencing_token", 0), int) or lease.get("fencing_token", 0) < 1: raise LeaseCorruptionError("execution lease entry has invalid fencing token")
        return data

    def _read_locked(self): return self._read()

    def _write(self, data):
        tmp = self.path.with_suffix(self.path.suffix + ".tmp")
        try:
            tmp.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")
            with tmp.open("r+", encoding="utf-8") as handle:
                handle.flush(); os.fsync(handle.fileno())
            tmp.replace(self.path)
        finally:
            if tmp.exists():
                try: tmp.unlink()
                except OSError: pass

    def acquire(self, execution_id: str, owner_id: str) -> Optional[ExecutionLease]:
        if not execution_id or not owner_id: raise ValueError("execution_id and owner_id are required")
        with self._lock():
            now = datetime.now(timezone.utc); data = self._read(); current = data.get(execution_id)
            if current and datetime.fromisoformat(current["expires_at"]) > now and current["owner_id"] != owner_id: return None
            token = int(current.get("fencing_token", 0)) + 1 if current else 1
            return self._store(execution_id, owner_id, data, now, token)

    def renew(self, execution_id: str, owner_id: str, fencing_token: Optional[int] = None) -> Optional[ExecutionLease]:
        with self._lock():
            now = datetime.now(timezone.utc); data = self._read(); current = data.get(execution_id)
            if not current or current["owner_id"] != owner_id or (fencing_token is not None and current["fencing_token"] != fencing_token) or datetime.fromisoformat(current["expires_at"]) <= now: return None
            return self._store(execution_id, owner_id, data, now, int(current["fencing_token"]))

    def is_owner(self, execution_id: str, owner_id: str, fencing_token: Optional[int] = None) -> bool:
        with self._lock():
            current = self._read().get(execution_id)
            return bool(current and current["owner_id"] == owner_id and (fencing_token is None or current["fencing_token"] == fencing_token) and datetime.fromisoformat(current["expires_at"]) > datetime.now(timezone.utc))

    def _store(self, execution_id, owner_id, data, now, fencing_token):
        lease = ExecutionLease(execution_id, owner_id, (now + timedelta(seconds=self.ttl_seconds)).isoformat(), fencing_token)
        data[execution_id] = {"owner_id": lease.owner_id, "expires_at": lease.expires_at, "fencing_token": lease.fencing_token}; self._write(data); return lease

    def release(self, execution_id: str, owner_id: str, fencing_token: Optional[int] = None) -> bool:
        with self._lock():
            data = self._read(); current = data.get(execution_id)
            if not current or current["owner_id"] != owner_id or (fencing_token is not None and current["fencing_token"] != fencing_token): return False
            current["owner_id"] = ""; current["expires_at"] = datetime.now(timezone.utc).isoformat(); self._write(data); return True
