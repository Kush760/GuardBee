"""SQLite persistence for GuardBee simulated audit decisions (stdlib only)."""

from __future__ import annotations

import json
import os
import sqlite3
from pathlib import Path
from typing import Any

# Default on-disk path; override with GUARDBEE_AUDIT_DB for tests or demos.
_DEFAULT_DB = Path(__file__).resolve().parent / "data" / "audit.db"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS audit_decisions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    time_utc TEXT NOT NULL,
    incident_id TEXT NOT NULL,
    actor TEXT NOT NULL,
    decision TEXT NOT NULL,
    outcome TEXT NOT NULL,
    simulation_only INTEGER NOT NULL,
    report_id TEXT NOT NULL UNIQUE,
    report_context_id TEXT,
    evidence_ids TEXT NOT NULL,
    policy_ids TEXT NOT NULL,
    status TEXT NOT NULL
);
"""


class AuditStoreError(RuntimeError):
    """Raised when an audit record cannot be persisted safely."""


def default_db_path() -> Path:
    override = os.getenv("GUARDBEE_AUDIT_DB", "").strip()
    return Path(override) if override else _DEFAULT_DB


def _connect(path: Path | None = None) -> sqlite3.Connection:
    db_path = path or default_db_path()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(str(db_path))
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON;")
    connection.executescript(_SCHEMA)
    return connection


def _row_to_record(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "time_utc": row["time_utc"],
        "incident_id": row["incident_id"],
        "actor": row["actor"],
        "decision": row["decision"],
        "outcome": row["outcome"],
        "simulation_only": bool(row["simulation_only"]),
        "report_id": row["report_id"],
        "report_context_id": row["report_context_id"],
        "evidence_ids": json.loads(row["evidence_ids"]),
        "policy_ids": json.loads(row["policy_ids"]),
        "status": row["status"],
    }


def get_decision_by_report_id(
    report_id: str, path: Path | None = None
) -> dict[str, Any] | None:
    if not report_id:
        return None
    with _connect(path) as connection:
        row = connection.execute(
            "SELECT * FROM audit_decisions WHERE report_id = ? LIMIT 1;",
            (report_id,),
        ).fetchone()
    return _row_to_record(row) if row else None


def list_decisions(path: Path | None = None) -> list[dict[str, Any]]:
    with _connect(path) as connection:
        rows = connection.execute(
            "SELECT * FROM audit_decisions ORDER BY id ASC;"
        ).fetchall()
    return [_row_to_record(row) for row in rows]


def save_decision(record: dict[str, Any], path: Path | None = None) -> dict[str, Any]:
    """Insert one simulated decision. Enforces one row per ``report_id``."""
    report_id = record.get("report_id")
    if not report_id:
        raise AuditStoreError("Audit record requires report_id.")
    if get_decision_by_report_id(str(report_id), path=path):
        raise AuditStoreError(
            f"A decision is already persisted for report_id={report_id!r}."
        )

    evidence_ids = list(record.get("evidence_ids") or [])
    policy_ids = list(record.get("policy_ids") or [])
    # Defense: never persist credential-like keys if a caller adds them by mistake.
    forbidden = {"api_key", "NEBIUS_API_KEY", "password", "secret", "token"}
    if forbidden.intersection(record):
        raise AuditStoreError("Refusing to persist secret-bearing audit fields.")

    payload = (
        record["time_utc"],
        record["incident_id"],
        record.get("actor", "demo-analyst"),
        record["decision"],
        record["outcome"],
        1 if record.get("simulation_only", True) else 0,
        str(report_id),
        record.get("report_context_id"),
        json.dumps(evidence_ids),
        json.dumps(policy_ids),
        record.get("status", "RECORDED"),
    )
    try:
        with _connect(path) as connection:
            connection.execute(
                """
                INSERT INTO audit_decisions (
                    time_utc, incident_id, actor, decision, outcome, simulation_only,
                    report_id, report_context_id, evidence_ids, policy_ids, status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                payload,
            )
            connection.commit()
    except sqlite3.IntegrityError as exc:
        raise AuditStoreError(
            f"A decision is already persisted for report_id={report_id!r}."
        ) from exc

    stored = get_decision_by_report_id(str(report_id), path=path)
    if stored is None:
        raise AuditStoreError("Persisted audit row could not be re-read.")
    return stored
