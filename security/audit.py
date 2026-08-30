from dataclasses import dataclass, field
from datetime import datetime, timezone

@dataclass
class AuditEvent:
    actor: str
    action: str
    resource: str
    result: str
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


def allow(action: str, permissions: set[str]) -> bool:
    return action in permissions
