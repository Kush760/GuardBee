"""Explainable, deterministic risk analysis for synthetic GuardBee incidents."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

# Configurable failure-burst window (MVP default: 30 minutes).
DEFAULT_FAILURE_BURST_WINDOW_MINUTES = 30

CLASSIFICATION_NORMAL = "NORMAL"
CLASSIFICATION_SUSPICIOUS = "SUSPICIOUS"
CLASSIFICATION_INSUFFICIENT = "INSUFFICIENT_EVIDENCE"

PRIORITY_NONE = "NONE"
PRIORITY_LOW = "LOW"
PRIORITY_MEDIUM = "MEDIUM"
PRIORITY_HIGH = "HIGH"


def _parse_event_time(event: dict[str, Any]) -> datetime | None:
    raw = event.get("time_utc")
    if not isinstance(raw, str) or not raw.strip():
        return None
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None


def _has_usable_ip(event: dict[str, Any]) -> bool:
    ip = event.get("ip")
    return isinstance(ip, str) and bool(ip.strip())


def _sort_events_chronologically(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Sort by timestamp; stable for equal times. Events with invalid times sort last."""
    indexed = list(enumerate(events))

    def sort_key(item: tuple[int, dict[str, Any]]) -> tuple[int, datetime, int]:
        index, event = item
        parsed = _parse_event_time(event)
        if parsed is None:
            return (1, datetime.min.replace(tzinfo=timezone.utc), index)
        return (0, parsed, index)

    return [event for _, event in sorted(indexed, key=sort_key)]


def _max_failure_burst(
    failures: list[dict[str, Any]], window: timedelta
) -> list[dict[str, Any]]:
    """Return the densest failure cluster that fits inside ``window``."""
    if not failures:
        return []
    ordered = [event for event in failures if _parse_event_time(event) is not None]
    ordered = _sort_events_chronologically(ordered)
    best: list[dict[str, Any]] = []
    for start_index, start_event in enumerate(ordered):
        start_time = _parse_event_time(start_event)
        assert start_time is not None
        cluster = [start_event]
        for later in ordered[start_index + 1 :]:
            later_time = _parse_event_time(later)
            assert later_time is not None
            if later_time - start_time <= window:
                cluster.append(later)
            else:
                break
        if len(cluster) > len(best):
            best = cluster
    return best


def _failures_before_success(
    events_sorted: list[dict[str, Any]], success: dict[str, Any], window: timedelta
) -> list[dict[str, Any]]:
    """Failures on the same IP that chronologically precede success within ``window``."""
    success_time = _parse_event_time(success)
    if success_time is None or not _has_usable_ip(success):
        return []
    ip = success["ip"]
    prior: list[dict[str, Any]] = []
    for event in events_sorted:
        if event.get("type") != "login_failed" or event.get("ip") != ip:
            continue
        event_time = _parse_event_time(event)
        if event_time is None:
            continue
        if event_time < success_time and success_time - event_time <= window:
            prior.append(event)
    return prior


def _severity_for_suspicious(score: int) -> str:
    if score >= 70:
        return "HIGH"
    if score >= 30:
        return "MEDIUM"
    return "LOW"


def _priority_for(classification: str, severity: str | None) -> str:
    if classification == CLASSIFICATION_NORMAL:
        return PRIORITY_NONE
    if classification == CLASSIFICATION_INSUFFICIENT:
        return PRIORITY_LOW
    if severity == "HIGH":
        return PRIORITY_HIGH
    if severity == "MEDIUM":
        return PRIORITY_MEDIUM
    return PRIORITY_LOW


def _suggested_action(classification: str, score: int) -> str:
    if classification == CLASSIFICATION_NORMAL:
        return "No containment recommendation; retain the event for normal monitoring"
    if classification == CLASSIFICATION_INSUFFICIENT:
        return (
            "Evidence is incomplete or inconclusive; gather additional context "
            "before containment. Do not treat this as confirmed compromise."
        )
    if score >= 70:
        return "Simulate session revocation and require a password reset"
    if score >= 30:
        return "Continue monitoring and verify the login with the account owner"
    return "Review supporting evidence; retain for investigation without immediate containment"


def analyze_incident(
    incident: dict[str, Any],
    *,
    failure_burst_window_minutes: int = DEFAULT_FAILURE_BURST_WINDOW_MINUTES,
) -> dict[str, Any]:
    """Return repeatable rule results; no AI is used to establish these facts.

    Classification, risk score, severity, and investigation priority are distinct:
    - ``classification``: NORMAL | SUSPICIOUS | INSUFFICIENT_EVIDENCE
    - ``risk_score``: numeric estimate capped at 100 (not proof of compromise)
    - ``severity``: HIGH/MEDIUM/LOW only for SUSPICIOUS; ``None`` otherwise
      (normal activity never receives LOW severity merely for a zero score)
    - ``investigation_priority``: NONE/LOW/MEDIUM/HIGH urgency for analyst review
    """
    if failure_burst_window_minutes <= 0:
        raise ValueError("failure_burst_window_minutes must be positive.")

    window = timedelta(minutes=failure_burst_window_minutes)
    raw_events = list(incident.get("events") or [])
    events = _sort_events_chronologically(raw_events)
    known_ips = {
        ip for ip in incident.get("known_ips", []) if isinstance(ip, str) and ip.strip()
    }

    # Incomplete IP context must not be treated as a normal or unfamiliar address.
    if any(not _has_usable_ip(event) for event in events):
        return {
            "risk_score": 0,
            "severity": None,
            "classification": CLASSIFICATION_INSUFFICIENT,
            "investigation_priority": PRIORITY_LOW,
            "rule_hits": [],
            "flags": ["Incomplete event context: missing or empty source IP"],
            "evidence_ids": [event["id"] for event in events if event.get("id")],
            "suggested_action": _suggested_action(CLASSIFICATION_INSUFFICIENT, 0),
        }

    if any(_parse_event_time(event) is None for event in events):
        return {
            "risk_score": 0,
            "severity": None,
            "classification": CLASSIFICATION_INSUFFICIENT,
            "investigation_priority": PRIORITY_LOW,
            "rule_hits": [],
            "flags": ["Incomplete event context: missing or invalid timestamps"],
            "evidence_ids": [event["id"] for event in events if event.get("id")],
            "suggested_action": _suggested_action(CLASSIFICATION_INSUFFICIENT, 0),
        }

    failures = [event for event in events if event["type"] == "login_failed"]
    successes = [event for event in events if event["type"] == "login_success"]
    burst = _max_failure_burst(failures, window)
    long_horizon_failures = len(failures) >= 3 and len(burst) < 3

    # Fail-then-success sequences (known or unfamiliar IP), chronological + windowed.
    sequences: list[dict[str, Any]] = []
    scored_success_ids: set[str] = set()
    for success in successes:
        prior = _failures_before_success(events, success, window)
        if len(prior) >= 3:
            sequences.append({"success": success, "failures": prior})
            scored_success_ids.add(success["id"])

    unfamiliar_successes = [
        event
        for event in successes
        if event["ip"] not in known_ips and event["id"] not in scored_success_ids
    ]

    rule_hits: list[dict[str, Any]] = []
    scored_failure_ids: set[str] = set()

    # GB-RULE-001: failure burst inside the configured window (once).
    if len(burst) >= 3:
        burst_ids = [event["id"] for event in burst]
        scored_failure_ids.update(burst_ids)
        rule_hits.append(
            {
                "rule_id": "GB-RULE-001",
                "flag": (
                    f"{len(burst)} failed login attempts within "
                    f"{failure_burst_window_minutes}-minute window"
                ),
                "points": 30,
                "evidence_ids": burst_ids,
            }
        )

    # GB-RULE-003: contextual fail-then-success (does not re-score the same failures).
    # Known IP is context only — not automatic safety. Unfamiliar increases weight.
    # Scope §3: the same underlying failure evidence must not inflate the score merely
    # because multiple later successes reference that same failure set. Independent
    # patterns (distinct failure evidence IDs) may still contribute separately.
    rule_003_by_failure_set: dict[frozenset[str], dict[str, Any]] = {}
    for pattern in sequences:
        success = pattern["success"]
        prior = pattern["failures"]
        failure_key = frozenset(event["id"] for event in prior)
        unfamiliar = success["ip"] not in known_ips
        points = 40 if unfamiliar else 25
        evidence = list(dict.fromkeys([event["id"] for event in prior] + [success["id"]]))
        ip_label = "unfamiliar" if unfamiliar else "known"
        existing = rule_003_by_failure_set.get(failure_key)
        if existing is not None:
            for event_id in evidence:
                if event_id not in existing["evidence_ids"]:
                    existing["evidence_ids"].append(event_id)
            continue
        hit = {
            "rule_id": "GB-RULE-003",
            "flag": (
                f"Failure burst followed by successful login from {ip_label} IP "
                f"{success['ip']}"
            ),
            "points": points,
            "evidence_ids": evidence,
        }
        rule_003_by_failure_set[failure_key] = hit
        rule_hits.append(hit)

    # GB-RULE-002: unfamiliar success alone is informational (0 points) — not automatic
    # proof of malicious activity. Classification becomes INSUFFICIENT_EVIDENCE unless
    # other suspicious rules already fired.
    if unfamiliar_successes and not sequences and len(burst) < 3:
        rule_hits.append(
            {
                "rule_id": "GB-RULE-002",
                "flag": "Successful login from an unfamiliar IP without supporting failure evidence",
                "points": 0,
                "evidence_ids": [event["id"] for event in unfamiliar_successes],
            }
        )

    # GB-RULE-006: longer-term failures outside any burst window (separate from RULE-001).
    if long_horizon_failures:
        rule_hits.append(
            {
                "rule_id": "GB-RULE-006",
                "flag": (
                    f"{len(failures)} failed logins observed outside any "
                    f"{failure_burst_window_minutes}-minute burst window"
                ),
                "points": 0,
                "evidence_ids": [event["id"] for event in failures],
            }
        )

    # Finance department must not add risk points (removed former GB-RULE-004 score bonus).

    score = min(sum(int(hit["points"]) for hit in rule_hits), 100)
    suspicious_points = any(int(hit["points"]) > 0 for hit in rule_hits)
    informational_only = bool(rule_hits) and not suspicious_points

    if suspicious_points:
        classification = CLASSIFICATION_SUSPICIOUS
        severity: str | None = _severity_for_suspicious(score)
    elif informational_only:
        classification = CLASSIFICATION_INSUFFICIENT
        severity = None
    else:
        classification = CLASSIFICATION_NORMAL
        severity = None

    evidence_ids = list(
        dict.fromkeys(event_id for hit in rule_hits for event_id in hit["evidence_ids"])
    )
    priority = _priority_for(classification, severity)

    return {
        "risk_score": score,
        "severity": severity,
        "classification": classification,
        "investigation_priority": priority,
        "rule_hits": rule_hits,
        "flags": [hit["flag"] for hit in rule_hits],
        "evidence_ids": evidence_ids,
        "suggested_action": _suggested_action(classification, score),
    }
