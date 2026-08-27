"""Transactional shared execution repository backed by SQLite.

SQLite provides a real shared-process transactional boundary and is suitable
for single-host multi-process deployments. It is deliberately not described
as a multi-host distributed database; deployments needing that guarantee can
implement the same repository protocol against Postgres/another transactional
store.
"""

import json
import sqlite3
from datetime import datetime, timezone
from typing import Any, Optional

from .execution_store import ExecutionConcurrencyError, ExecutionState


class SQLiteExecutionRepository:
    def __init__(self, path: str):
        self.path = path
        with self._connect() as db:
            db.execute("PRAGMA journal_mode=WAL")
            db.execute("PRAGMA busy_timeout=5000")
            db.execute("CREATE TABLE IF NOT EXISTS executions (execution_id TEXT PRIMARY KEY, state_json TEXT NOT NULL, version INTEGER NOT NULL, fencing_token INTEGER)")

    def _connect(self):
        return sqlite3.connect(self.path, timeout=5, isolation_level=None)

    def get(self, execution_id: str) -> Optional[ExecutionState]:
        with self._connect() as db:
            row = db.execute("SELECT state_json FROM executions WHERE execution_id = ?", (execution_id,)).fetchone()
        return ExecutionState(**json.loads(row[0])) if row else None

    def create(self, state: ExecutionState) -> ExecutionState:
        payload = json.dumps(state.__dict__, ensure_ascii=False)
        try:
            with self._connect() as db:
                db.execute("INSERT INTO executions(execution_id,state_json,version,fencing_token) VALUES(?,?,?,?)", (state.execution_id, payload, state.version, state.fencing_token))
        except sqlite3.IntegrityError as exc:
            raise ExecutionConcurrencyError("execution already exists") from exc
        return self.get(state.execution_id)

    def compare_and_set(self, execution_id: str, *, expected_version: int, fencing_token: Optional[int], status: str, **updates: Any) -> ExecutionState:
        now = datetime.now(timezone.utc).isoformat()
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT state_json, version, fencing_token FROM executions WHERE execution_id = ?", (execution_id,)).fetchone()
            if row is None:
                db.rollback()
                raise KeyError(execution_id)
            state = ExecutionState(**json.loads(row[0]))
            if state.version != expected_version:
                db.rollback()
                raise ExecutionConcurrencyError("version conflict")
            if fencing_token is not None and state.fencing_token != fencing_token:
                db.rollback()
                raise ExecutionConcurrencyError("fencing conflict")
            state.status = status
            for key, value in updates.items():
                setattr(state, key, value)
            state.version += 1
            state.updated_at = now
            db.execute("UPDATE executions SET state_json = ?, version = ?, fencing_token = ? WHERE execution_id = ? AND version = ?", (json.dumps(state.__dict__, ensure_ascii=False), state.version, state.fencing_token, execution_id, expected_version))
            db.commit()
            return state
