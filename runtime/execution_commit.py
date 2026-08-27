"""Crash-recoverable execution commit protocol with an integrity-protected journal."""

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any, Optional

from .execution_audit import ExecutionAuditEvent, ExecutionAuditLog
from .execution_store import ExecutionFencingConflictError, ExecutionState, ExecutionStore

try:
    import fcntl
except ImportError:  # pragma: no cover
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

    def with_integrity(self):
        if self.checksum:
            return self
        payload = asdict(self)
        payload.pop("checksum", None)
        raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str)
        return ExecutionCommit(**{**payload, "checksum": hashlib.sha256(raw.encode()).hexdigest()})


class CorruptJournalError(ValueError):
    pass


class _JournalLock:
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


class ExecutionCommitCoordinator:
    def __init__(self, store: ExecutionStore, audit_log: ExecutionAuditLog, journal_path: str = "data/execution_commits.jsonl", quarantine_path: str = "data/execution_commits.quarantine.jsonl", lease_store=None, lease_owner_id: Optional[str] = None, fencing_token: Optional[int] = None):
        self.store = store
        self.audit_log = audit_log
        self.journal_path = Path(journal_path)
        self.quarantine_path = Path(quarantine_path)
        self.lease_store = lease_store
        self.lease_owner_id = lease_owner_id
        self.fencing_token = fencing_token
        self.journal_path.parent.mkdir(parents=True, exist_ok=True)
        self.lock_path = self.journal_path.with_suffix(self.journal_path.suffix + ".lock")

    def _next_sequence_unlocked(self):
        if not self.journal_path.exists():
            return 1
        maximum = 0
        for line in self.journal_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                maximum = max(maximum, int(json.loads(line).get("sequence", 0)))
            except (json.JSONDecodeError, TypeError, ValueError, AttributeError):
                continue
        return maximum + 1

    def _append_journal(self, commit):
        with _JournalLock(self.lock_path):
            commit = ExecutionCommit(**{**asdict(commit), "sequence": self._next_sequence_unlocked()}).with_integrity()
            with self.journal_path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(asdict(commit), ensure_ascii=False, default=str) + "\n")
                handle.flush()
                import os
                os.fsync(handle.fileno())
            return commit

    def _read_journal(self):
        if not self.journal_path.exists():
            return []
        result = []
        expected = 1
        for line in self.journal_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            raw = {}
            try:
                raw = json.loads(line)
                sequence = int(raw.get("sequence", expected))
                raw.setdefault("status", "pending")
                raw.setdefault("sequence", sequence)
                commit = ExecutionCommit(**raw)
                if commit.sequence != expected or commit.with_integrity().checksum != commit.checksum:
                    raise CorruptJournalError(f"invalid journal integrity at sequence {expected}")
            except (json.JSONDecodeError, TypeError, KeyError, ValueError, CorruptJournalError) as exc:
                self._quarantine(line, str(exc))
                expected = max(expected + 1, int(raw.get("sequence", 0)) + 1) if isinstance(raw, dict) else expected + 1
                continue
            result.append(commit)
            expected = commit.sequence + 1
        return result

    def _quarantine(self, line, reason):
        with self.quarantine_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps({"reason": reason, "line": line, "quarantined_at": datetime.now(timezone.utc).isoformat()}, ensure_ascii=False) + "\n")

    def _lease_valid(self, execution_id):
        if self.lease_store is None:
            return True
        if not self.lease_owner_id or self.fencing_token is None:
            return False
        return self.lease_store.is_owner(execution_id, self.lease_owner_id, self.fencing_token)

    def _fencing_validator(self, execution_id, token):
        return self._lease_valid(execution_id) and token == self.fencing_token

    def commit(self, state, to_status, *, checkpoint=None, reason=None):
        current = self.store.get(state.execution_id) or state
        if not self._lease_valid(current.execution_id):
            raise PermissionError("execution lease is not held by the current fencing token")
        commit_id = f"{current.execution_id}:{current.attempt}:{to_status}:{current.correlation_id or ''}"
        existing = {c.commit_id: c for c in self.pending(all_statuses=True)}.get(commit_id)
        if existing:
            return existing
        commit = self._append_journal(ExecutionCommit(commit_id, current.execution_id, current.status, to_status, current.attempt, checkpoint, reason, correlation_id=current.correlation_id))
        try:
            self.store.compare_and_set(
                ExecutionState(**{**asdict(current), "status": to_status, "result": checkpoint if to_status == "completed" else current.result, "error": reason if to_status == "failed" else current.error}),
                current.version,
                expected_status=current.status,
                fencing_token=self.fencing_token,
                fencing_validator=self._fencing_validator,
            )
        except (ExecutionFencingConflictError, PermissionError):
            return commit
        except Exception:
            return commit
        self.audit_log.append(ExecutionAuditEvent(current.execution_id, current.status, to_status, current.attempt, reason, correlation_id=current.correlation_id, event_id=commit_id))
        self._mark(commit_id, "applied")
        return commit

    def _mark(self, commit_id, status):
        with _JournalLock(self.lock_path):
            commits = self._read_journal()
            for i, commit in enumerate(commits):
                if commit.commit_id == commit_id:
                    commits[i] = ExecutionCommit(**{**asdict(commit), "status": status}).with_integrity()
                    break
            tmp = self.journal_path.with_suffix(self.journal_path.suffix + ".tmp")
            tmp.write_text("".join(json.dumps(asdict(c.with_integrity()), ensure_ascii=False, default=str) + "\n" for c in commits), encoding="utf-8")
            with tmp.open("r+", encoding="utf-8") as handle:
                handle.flush()
                import os
                os.fsync(handle.fileno())
            tmp.replace(self.journal_path)

    def reconcile(self):
        repaired = []
        for commit in self.pending():
            state = self.store.get(commit.execution_id)
            if not state or not self._lease_valid(commit.execution_id):
                continue
            if state.status == commit.to_status:
                self.audit_log.append(ExecutionAuditEvent(commit.execution_id, commit.from_status, commit.to_status, commit.attempt, commit.reason, correlation_id=commit.correlation_id, event_id=commit.commit_id))
                self._mark(commit.commit_id, "reconciled")
                repaired.append(commit.commit_id)
                continue
            if state.status != commit.from_status:
                continue
            try:
                self.store.compare_and_set(
                    ExecutionState(**{**asdict(state), "status": commit.to_status, "result": commit.checkpoint if commit.to_status == "completed" else state.result, "error": commit.reason if commit.to_status == "failed" else state.error}),
                    state.version,
                    expected_status=commit.from_status,
                    fencing_token=self.fencing_token,
                    fencing_validator=self._fencing_validator,
                )
            except (ExecutionFencingConflictError, PermissionError, Exception):
                continue
            self.audit_log.append(ExecutionAuditEvent(commit.execution_id, commit.from_status, commit.to_status, commit.attempt, commit.reason, correlation_id=commit.correlation_id, event_id=commit.commit_id))
            self._mark(commit.commit_id, "reconciled")
            repaired.append(commit.commit_id)
        return repaired

    def pending(self, all_statuses=False):
        commits = self._read_journal()
        return commits if all_statuses else [c for c in commits if c.status == "pending"]
