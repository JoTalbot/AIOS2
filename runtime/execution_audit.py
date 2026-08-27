"""Structured and persistent audit trail for vNext execution lifecycle."""

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from .execution_context import ExecutionContext
from .execution_events import ExecutionEvent

try:
    import fcntl
except ImportError:  # pragma: no cover
    fcntl = None


@dataclass(frozen=True)
class ExecutionAuditEvent:
    execution_id: str
    from_status: str
    to_status: str
    attempt: int = 0
    reason: Optional[str] = None
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    event_id: str = ""
    correlation_id: Optional[str] = None

    def with_identity(self):
        if self.event_id:
            return self
        payload = f"{self.execution_id}|{self.from_status}|{self.to_status}|{self.attempt}|{self.reason}|{self.timestamp}|{self.correlation_id}"
        return ExecutionAuditEvent(**{**asdict(self), "event_id": hashlib.sha256(payload.encode()).hexdigest()})


@dataclass
class AuditEvent:
    event: str
    agent_id: str
    tool: Optional[str] = None
    status: str = "ok"
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    execution_id: Optional[str] = None
    correlation_id: Optional[str] = None


class _AuditLock:
    def __init__(self, path: Path):
        self.path = path
        self.handle = None

    def __enter__(self):
        self.path.touch(exist_ok=True)
        self.handle = self.path.open("r+", encoding="utf-8")
        if fcntl is not None:
            fcntl.flock(self.handle.fileno(), fcntl.LOCK_EX)
        return self

    def __exit__(self, exc_type, exc, tb):
        if fcntl is not None:
            fcntl.flock(self.handle.fileno(), fcntl.LOCK_UN)
        self.handle.close()


class ExecutionAuditLog:
    def __init__(self, path: str = "data/execution_audit.jsonl"):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.lock_path = self.path.with_suffix(self.path.suffix + ".lock")

    def append(self, event: ExecutionAuditEvent):
        event = event.with_identity()
        with _AuditLock(self.lock_path):
            if self._contains(event.event_id):
                return event
            with self.path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(asdict(event), ensure_ascii=False) + "\n")
                handle.flush()
                import os
                os.fsync(handle.fileno())
        return event

    def _contains(self, event_id):
        if not self.path.exists():
            return False
        return any(json.loads(line).get("event_id") == event_id for line in self.path.read_text(encoding="utf-8").splitlines() if line.strip())

    def events(self, execution_id=None):
        if not self.path.exists():
            return []
        result = []
        for line in self.path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                event = ExecutionAuditEvent(**json.loads(line))
                if execution_id is None or event.execution_id == execution_id:
                    result.append(event)
        return result


class ExecutionAudit:
    def __init__(self):
        self.events: List[AuditEvent] = []

    def record(self, event: str, agent_id: str, tool: Optional[str] = None, status: str = "ok", context: Optional[ExecutionContext] = None, correlation_id: Optional[str] = None, **metadata):
        item = AuditEvent(event, agent_id, tool, status, metadata, execution_id=getattr(context, "execution_id", None), correlation_id=correlation_id)
        self.events.append(item)
        return item

    def record_event(self, event: ExecutionEvent):
        return self.record(event.type, event.context.agent_id, context=event.context, **event.data)

    def snapshot(self):
        return list(self.events)
