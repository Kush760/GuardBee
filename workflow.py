"""Pure decision-gate helpers shared by GuardBee's Streamlit workflow and tests."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any


def analysis_context_id(
    incident: dict[str, Any], analysis: dict[str, Any], policies: list[dict[str, Any]]
) -> str:
    """Fingerprint exactly the evidence and retrieved policies shown for an analysis."""
    context = {
        "incident": incident,
        "analysis": analysis,
        "retrieved_policy_ids": [policy["id"] for policy in policies],
    }
    encoded = json.dumps(context, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def can_record_decision(
    report: str | None,
    report_context_id: str | None,
    current_context_id: str,
    report_id: str | None,
    existing_decision: dict[str, Any] | None,
) -> bool:
    """Allow one human decision only for the current, validated AI report."""
    if not report or report_context_id != current_context_id or not report_id:
        return False
    return not existing_decision or existing_decision.get("report_id") != report_id


def build_decision_record(
    incident_id: str,
    decision: str,
    outcome: str,
    report: str | None,
    report_context_id: str | None,
    current_context_id: str,
    report_id: str | None,
    existing_decision: dict[str, Any] | None,
    now: datetime | None = None,
    evidence_ids: list[str] | None = None,
    policy_ids: list[str] | None = None,
) -> dict[str, Any] | None:
    """Return a simulated audit record, or None if its decision gate is closed.

    Records include evidence/policy references and status for SQLite persistence
    (MVP Scope v2.2 §6). Secrets must never be placed on this record.
    """
    if decision not in {"APPROVED", "REJECTED"}:
        raise ValueError("decision must be APPROVED or REJECTED")
    if not can_record_decision(
        report, report_context_id, current_context_id, report_id, existing_decision
    ):
        return None
    timestamp = now or datetime.now(timezone.utc)
    return {
        "time_utc": timestamp.isoformat(timespec="seconds"),
        "incident_id": incident_id,
        "actor": "demo-analyst",
        "decision": decision,
        "outcome": outcome,
        "simulation_only": True,
        "report_id": report_id,
        "report_context_id": report_context_id,
        "evidence_ids": list(evidence_ids or []),
        "policy_ids": list(policy_ids or []),
        "status": "RECORDED",
    }
