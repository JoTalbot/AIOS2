"""Persistent execution state with fail-closed optimistic CAS and fencing."""
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import json
import os
from pathlib import Path
from typing import Any, Callable, Optional

from .execution_audit import ExecutionAuditEvent
from .execution_state_machine import ExecutionStateMachine
from .tool_protocol import ToolResult

try:
    import fcntl
except ImportError:  # pragma: no cover
    fcntl = None


class ExecutionStoreCorruptionError(RuntimeError):
    pass


class ExecutionVersionConflictError(RuntimeError):
    pass


class ExecutionFencingConflictError(RuntimeError):
    pass


@dataclass
class ExecutionState:
    execution_id: str
    status: str = "pending"
    goal: str = ""
    attempt: int = 0
    plan: Any = None
    result: Any = None
    error: Optional[str] = None
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    correlation_id: Optional[str] = None
    version: int = 0


class _FileLock:
    def __init__(self, path):
        self.path, self.handle = Path(path), None

    def __enter__(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.touch(exist_ok=True)
        self.handle = self.path.open("r+", encoding="utf-8")
        if fcntl is not None:
            fcntl.flock(self.handle.fileno(), fcntl.LOCK_EX)
        return self

    def __exit__(self, exc_type, exc, tb):
        if fcntl is not None:
            fcntl.flock(self.handle.fileno(), fcntl.LOCK_UN)
        self.handle.close()


class ExecutionStore:
    def __init__(
        self,
        path="data/executions.json",
        state_machine=None,
        audit_log=None,
        coordination_lock_path=None,
        fencing_validator: Optional[Callable[[str, Any], bool]] = None,
    ):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.lock_path = self.path.with_suffix(self.path.suffix + ".lock")
        self.coordination_lock_path = Path(coordination_lock_path) if coordination_lock_path else None
        self.state_machine = state_machine or ExecutionStateMachine()
        self.audit_log = audit_log
        self.fencing_validator = fencing_validator
        with self.execution_lock():
            if not self.path.exists():
                self._write({})

    def execution_lock(self):
        return _FileLock(self.coordination_lock_path or self.lock_path)

    def _read_unlocked(self):
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            return {}
        except json.JSONDecodeError as exc:
            raise ExecutionStoreCorruptionError(
                f"execution store contains invalid JSON: {self.path}"
            ) from exc
        if not isinstance(data, dict):
            raise ExecutionStoreCorruptionError(
                f"execution store root must be an object: {self.path}"
            )
        return data

    def _write(self, data):
        tmp = self.path.with_suffix(self.path.suffix + ".tmp")
        try:
            with tmp.open("w", encoding="utf-8") as handle:
                json.dump(data, handle, ensure_ascii=False, default=str, indent=2)
                handle.flush()
                os.fsync(handle.fileno())
            tmp.replace(self.path)
        finally:
            if tmp.exists():
                try:
                    tmp.unlink()
                except OSError:
                    pass

    @staticmethod
    def _version(raw):
        if raw is None:
            return 0
        value = raw.get("version", 0)
        if not isinstance(value, int) or isinstance(value, bool) or value < 0:
            raise ExecutionStoreCorruptionError("execution state has invalid version")
        return value

    @staticmethod
    def _decode_value(value):
        if isinstance(value, list):
            return [ExecutionStore._decode_value(x) for x in value]
        if isinstance(value, dict):
            if {"call_id", "tool", "ok"}.issubset(value):
                try:
                    return ToolResult(
                        value["call_id"],
                        value["tool"],
                        bool(value["ok"]),
                        ExecutionStore._decode_value(value.get("value")),
                        value.get("error"),
                        bool(value.get("retryable", False)),
                        value.get("idempotency_key"),
                    )
                except Exception:
                    pass
            return {k: ExecutionStore._decode_value(v) for k, v in value.items()}
        return value

    def _decode_state(self, raw):
        if not raw:
            return None
        value = dict(raw)
        value["result"] = self._decode_value(value.get("result"))
        return ExecutionState(**value)

    def _get_unlocked(self, execution_id):
        return self._decode_state(self._read_unlocked().get(execution_id))

    def execution_ids(self):
        with self.execution_lock():
            return list(self._read_unlocked())

    def save(self, state, *, fencing_token=None, fencing_validator=None):
        """Create or update using the state's observed version; never last-write-wins."""
        if not isinstance(state, ExecutionState):
            raise TypeError("state must be an ExecutionState")
        return self._save(
            state,
            state.version,
            validate_transition=False,
            fencing_token=fencing_token,
            fencing_validator=fencing_validator,
        )

    def compare_and_set(
        self,
        state,
        expected_version,
        *,
        expected_status=None,
        fencing_token=None,
        fencing_validator=None,
        lock_held=False,
    ):
        if not isinstance(expected_version, int) or isinstance(expected_version, bool) or expected_version < 0:
            raise ValueError("expected_version must be a non-negative integer")
        if lock_held:
            return self._save_unlocked(
                state,
                expected_version,
                True,
                expected_status=expected_status,
                fencing_token=fencing_token,
                fencing_validator=fencing_validator,
            )
        return self._save(
            state,
            expected_version,
            True,
            expected_status=expected_status,
            fencing_token=fencing_token,
            fencing_validator=fencing_validator,
        )

    def _save(self, state, expected_version, validate_transition=True, **kwargs):
        with self.execution_lock():
            return self._save_unlocked(state, expected_version, validate_transition, **kwargs)

    def _save_unlocked(
        self,
        state,
        expected_version,
        validate_transition=True,
        *,
        expected_status=None,
        fencing_token=None,
        fencing_validator=None,
    ):
        if not isinstance(state, ExecutionState):
            raise TypeError("state must be an ExecutionState")
        if not state.execution_id or not isinstance(state.execution_id, str):
            raise ValueError("execution_id must be a non-empty string")
        if expected_version is None:
            raise ValueError("expected_version is required at the persistence boundary")

        data = self._read_unlocked()
        previous = data.get(state.execution_id)
        current_version = self._version(previous)
        if current_version != expected_version:
            raise ExecutionVersionConflictError(
                f"execution '{state.execution_id}' version changed"
            )
        if previous is not None and state.version != current_version:
            raise ExecutionVersionConflictError(
                f"execution '{state.execution_id}' state carries stale version"
            )
        if expected_status is not None and (previous or {}).get("status", "pending") != expected_status:
            raise ExecutionVersionConflictError(
                f"execution '{state.execution_id}' status changed"
            )

        validator = fencing_validator or self.fencing_validator
        if fencing_token is not None and validator is None:
            raise ExecutionFencingConflictError("fencing token requires a fencing validator")
        if validator is not None and not validator(state.execution_id, fencing_token):
            raise ExecutionFencingConflictError(
                f"execution '{state.execution_id}' fencing token is stale"
            )

        if previous and validate_transition:
            self.state_machine.validate(previous.get("status", "pending"), state.status)

        old_status = previous.get("status", "pending") if previous else None
        persisted = ExecutionState(
            **{
                **asdict(state),
                "version": current_version + 1,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
        )
        data[state.execution_id] = asdict(persisted)
        # Do not mutate the caller's object until the durable rename succeeds.
        self._write(data)
        state.version = persisted.version
        state.updated_at = persisted.updated_at

        if self.audit_log and old_status != state.status:
            self.audit_log.append(
                ExecutionAuditEvent(
                    state.execution_id,
                    old_status or "new",
                    state.status,
                    state.attempt,
                    state.error,
                    correlation_id=state.correlation_id,
                )
            )
        return state

    def transition(
        self,
        execution_id,
        status,
        *,
        fencing_token=None,
        fencing_validator=None,
        **updates,
    ):
        state = self.get(execution_id)
        if not state:
            if status != "pending":
                raise KeyError(execution_id)
            state = ExecutionState(execution_id=execution_id)
        state.status = status
        for key, value in updates.items():
            setattr(state, key, value)
        return self.compare_and_set(
            state,
            state.version,
            fencing_token=fencing_token,
            fencing_validator=fencing_validator,
        )

    def get(self, execution_id):
        with self.execution_lock():
            return self._get_unlocked(execution_id)

    def resumable(self):
        with self.execution_lock():
            values = list(self._read_unlocked().values())
        return [
            ExecutionState(**{**raw, "result": self._decode_value(raw.get("result"))})
            for raw in values
            if raw.get("status") in {"running", "retrying"}
            or (raw.get("status") == "pending" and raw.get("attempt", 0) > 0)
        ]
