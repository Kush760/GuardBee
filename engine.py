"""Explainable, deterministic risk analysis for synthetic GuardBee incidents."""

from __future__ import annotations

from typing import Any


def analyze_incident(incident: dict[str, Any]) -> dict[str, Any]:
    """Return repeatable rule results; no AI is used to establish these facts."""
    events = incident["events"]
    failures = [event for event in events if event["type"] == "login_failed"]
    successes = [event for event in events if event["type"] == "login_success"]
    known_ips = set(incident.get("known_ips", []))
    unfamiliar_successes = [event for event in successes if event["ip"] not in known_ips]
    shared_ips = {event["ip"] for event in failures} & {
        event["ip"] for event in unfamiliar_successes
    }

    rule_hits: list[dict[str, Any]] = []
    if len(failures) >= 3:
        rule_hits.append(
            {
                "rule_id": "GB-RULE-001",
                "flag": f"{len(failures)} failed login attempts",
                "points": 30,
                "evidence_ids": [event["id"] for event in failures],
            }
        )
    if unfamiliar_successes:
        rule_hits.append(
            {
                "rule_id": "GB-RULE-002",
                "flag": "Successful login from an unfamiliar IP",
                "points": 40,
                "evidence_ids": [event["id"] for event in unfamiliar_successes],
            }
        )
    if shared_ips:
        related = [
            event["id"]
            for event in events
            if event["ip"] in shared_ips and event["type"] in {"login_failed", "login_success"}
        ]
        rule_hits.append(
            {
                "rule_id": "GB-RULE-003",
                "flag": "Failed and successful attempts share an unfamiliar IP",
                "points": 15,
                "evidence_ids": related,
            }
        )
    if rule_hits and incident.get("department") == "Finance":
        rule_hits.append(
            {
                "rule_id": "GB-RULE-004",
                "flag": "Sensitive Finance account requires priority review",
                "points": 10,
                "evidence_ids": [],
            }
        )

    score = min(sum(hit["points"] for hit in rule_hits), 100)
    severity = "HIGH" if score >= 70 else "MEDIUM" if score >= 30 else "LOW"
    evidence_ids = list(
        dict.fromkeys(event_id for hit in rule_hits for event_id in hit["evidence_ids"])
    )
    suggested_action = (
        "Simulate session revocation and require a password reset"
        if score >= 70
        else "Continue monitoring and verify the login with the account owner"
        if score >= 30
        else "No containment recommendation; retain the event for normal monitoring"
    )
    return {
        "risk_score": score,
        "severity": severity,
        "rule_hits": rule_hits,
        "flags": [hit["flag"] for hit in rule_hits],
        "evidence_ids": evidence_ids,
        "suggested_action": suggested_action,
    }
