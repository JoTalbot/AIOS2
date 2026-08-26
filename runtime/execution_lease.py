"""Process-safe file-backed execution lease with renewal for recovery."""

from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
from typing import Optional

try:
    import fcntl
except ImportError:  # pragma: no cover - Windows fallback keeps API usable.
    fcntl = None


@dataclass(frozen=True)
class ExecutionLease:
    execution_id: str
    owner_id: str
    expires_at: str


class ExecutionLeaseStore:
    def __init__(self, path: str = "data/execution_leases.json", ttl_seconds: int = 60):
        self.path = Path(path)
        self.lock_path = self.path.with_suffix(self.path.suffix + ".lock")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.ttl_seconds = max(1, ttl_seconds)
        if not self.path.exists():
            self._write({})

    @contextmanager
    def _lock(self):
        """Serialize read-modify-write lease operations across processes."""
        with self.lock_path.open("a+", encoding="utf-8") as handle:
            if fcntl is not None:
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
            try:
                yield
            finally:
                if fcntl is not None:
                    fcntl.flock(handle.fileno(), fcntl.LOCK_UN)

    def _read(self):
        try:
            return json.loads(self.path.read_text(encoding="utf-8"))
        except (FileNotFoundError, json.JSONDecodeError):
            return {}

    def _write(self, data):
        tmp = self.path.with_suffix(self.path.suffix + ".tmp")
        tmp.write_text(json.dumps(data, indent=2), encoding="utf-8")
        tmp.replace(self.path)

    def acquire(self, execution_id: str, owner_id: str) -> Optional[ExecutionLease]:
        now = datetime.now(timezone.utc)
        with self._lock():
            data = self._read()
            current = data.get(execution_id)
            if current and datetime.fromisoformat(current["expires_at"]) > now and current["owner_id"] != owner_id:
                return None
            return self._store(execution_id, owner_id, data, now)

    def renew(self, execution_id: str, owner_id: str) -> Optional[ExecutionLease]:
        now = datetime.now(timezone.utc)
        with self._lock():
            data = self._read()
            current = data.get(execution_id)
            if not current or current["owner_id"] != owner_id or datetime.fromisoformat(current["expires_at"]) <= now:
                return None
            return self._store(execution_id, owner_id, data, now)

    def is_owner(self, execution_id: str, owner_id: str) -> bool:
        with self._lock():
            current = self._read().get(execution_id)
            return bool(current and current["owner_id"] == owner_id and datetime.fromisoformat(current["expires_at"]) > datetime.now(timezone.utc))

    def _store(self, execution_id, owner_id, data, now):
        lease = ExecutionLease(execution_id, owner_id, (now + timedelta(seconds=self.ttl_seconds)).isoformat())
        data[execution_id] = {"owner_id": lease.owner_id, "expires_at": lease.expires_at}
        self._write(data)
        return lease

    def release(self, execution_id: str, owner_id: str) -> bool:
        with self._lock():
            data = self._read()
            current = data.get(execution_id)
            if not current or current["owner_id"] != owner_id:
                return False
            del data[execution_id]
            self._write(data)
            return True
