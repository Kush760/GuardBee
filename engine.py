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

# Dynamic scoring (v2.3). Every point comes from the incident's own events.
POINTS_PER_BURST_FAILURE = 5
MAX_BURST_POINTS = 30
SPEED_POINTS_PER_FAILURE_PER_MINUTE = 5
MAX_SPEED_POINTS = 10
FIRST_SUCCESS_POINTS = 15
EXTRA_SUCCESS_POINTS = 5
MAX_SUCCESS_POINTS = 25
UNFAMILIAR_SUCCESS_POINTS = 15
EXTRA_UNFAMILIAR_IP_POINTS = 4
MAX_EXTRA_UNFAMILIAR_IP_POINTS = 8
NEW_COUNTRY_POINTS = 10
IMPOSSIBLE_TRAVEL_POINTS = 15
IMPOSSIBLE_TRAVEL_HOURS = 3
OFF_HOURS_POINTS = 4
OFF_HOURS_UTC = range(0, 5)  # 00:00-04:59 UTC
KNOWN_ONLY_POINTS = -10

# Severity comes from the score, never the other way round.
SEVERITY_BANDS = (("CRITICAL", 85), ("HIGH", 65), ("MEDIUM", 40), ("LOW", 0))
UNKNOWN_COUNTRY = "Unknown"


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


def _country(event: dict[str, Any]) -> str:
    country = event.get("country")
    return country.strip() if isinstance(country, str) and country.strip() else UNKNOWN_COUNTRY


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


def _burst_speed_points(burst: list[dict[str, Any]]) -> tuple[int, float]:
    """Points for how fast the burst arrived, and the burst span in minutes."""
    times = [_parse_event_time(event) for event in burst]
    span = (max(times) - min(times)).total_seconds() / 60  # type: ignore[type-var]
    rate = (len(burst) - 1) / span if span > 0 else float(len(burst))
    points = int(rate * SPEED_POINTS_PER_FAILURE_PER_MINUTE + 0.5)  # round half up
    return min(MAX_SPEED_POINTS, points), span


def _home_countries(incident: dict[str, Any], events: list[dict[str, Any]], known_ips: set[str]) -> set[str]:
    """The account's usual countries: its declared home plus wherever its known IPs signed in."""
    home = {_country(event) for event in events if event["ip"] in known_ips}
    declared = incident.get("home_country")
    if isinstance(declared, str) and declared.strip():
        home.add(declared.strip())
    home.discard(UNKNOWN_COUNTRY)
    return home


def _impossible_travel(successes: list[dict[str, Any]]) -> tuple[dict[str, Any], dict[str, Any], int] | None:
    """First pair of consecutive sign-ins from two different countries too close in time to travel."""
    located = [event for event in successes if _country(event) != UNKNOWN_COUNTRY]
    for earlier, later in zip(located, located[1:]):
        gap = _parse_event_time(later) - _parse_event_time(earlier)  # type: ignore[operator]
        if _country(earlier) != _country(later) and gap <= timedelta(hours=IMPOSSIBLE_TRAVEL_HOURS):
            return earlier, later, int(gap.total_seconds() // 60)
    return None


def _severity_for_suspicious(score: int) -> str:
    for severity, floor in SEVERITY_BANDS:
        if score >= floor:
            return severity
    return "LOW"


def _priority_for(classification: str, severity: str | None) -> str:
    if classification == CLASSIFICATION_NORMAL:
        return PRIORITY_NONE
    if classification == CLASSIFICATION_INSUFFICIENT:
        return PRIORITY_LOW
    if severity in ("CRITICAL", "HIGH"):
        return PRIORITY_HIGH
    if severity == "MEDIUM":
        return PRIORITY_MEDIUM
    return PRIORITY_LOW


def _suggested_action(classification: str, severity: str | None) -> str:
    if classification == CLASSIFICATION_NORMAL:
        return "No containment recommendation; retain the event for normal monitoring"
    if classification == CLASSIFICATION_INSUFFICIENT:
        return (
            "Evidence is incomplete or inconclusive; gather additional context "
            "before containment. Do not treat this as confirmed compromise."
        )
    if severity in ("CRITICAL", "HIGH"):
        return "Simulate session revocation and require a password reset"
    if severity == "MEDIUM":
        return "Continue monitoring and verify the login with the account owner"
    return "Review supporting evidence; retain for investigation without immediate containment"


def _insufficient(flag: str, events: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "risk_score": 0,
        "severity": None,
        "classification": CLASSIFICATION_INSUFFICIENT,
        "investigation_priority": PRIORITY_LOW,
        "rule_hits": [],
        "flags": [flag],
        "evidence_ids": [event["id"] for event in events if event.get("id")],
        "suggested_action": _suggested_action(CLASSIFICATION_INSUFFICIENT, None),
    }


def analyze_incident(
    incident: dict[str, Any],
    *,
    failure_burst_window_minutes: int = DEFAULT_FAILURE_BURST_WINDOW_MINUTES,
) -> dict[str, Any]:
    """Return repeatable rule results; no AI is used to establish these facts.

    Classification, risk score, severity, and investigation priority are distinct:
    - ``classification``: NORMAL | SUSPICIOUS | INSUFFICIENT_EVIDENCE
    - ``risk_score``: numeric estimate capped at 100 (not proof of compromise), built
      from the incident's own events; every point is a rule hit with evidence IDs
    - ``severity``: CRITICAL/HIGH/MEDIUM/LOW from score bands, only for SUSPICIOUS;
      ``None`` otherwise (normal activity never receives LOW severity for a zero score)
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
        return _insufficient("Incomplete event context: missing or empty source IP", events)
    if any(_parse_event_time(event) is None for event in events):
        return _insufficient("Incomplete event context: missing or invalid timestamps", events)

    failures = [event for event in events if event["type"] == "login_failed"]
    successes = [event for event in events if event["type"] == "login_success"]
    burst = _max_failure_burst(failures, window)
    long_horizon_failures = len(failures) >= 3 and len(burst) < 3

    # Fail-then-success sequences (known or unfamiliar IP), chronological + windowed.
    sequence_successes: list[dict[str, Any]] = []
    sequence_failure_ids: list[str] = []
    for success in successes:
        prior = _failures_before_success(events, success, window)
        if len(prior) >= 3:
            sequence_successes.append(success)
            sequence_failure_ids.extend(event["id"] for event in prior)
    sequence_failure_ids = list(dict.fromkeys(sequence_failure_ids))
    scored_success_ids = {event["id"] for event in sequence_successes}

    unfamiliar_successes = [
        event
        for event in successes
        if event["ip"] not in known_ips and event["id"] not in scored_success_ids
    ]

    rule_hits: list[dict[str, Any]] = []

    def hit(rule_id: str, flag: str, points: int, evidence: list[dict[str, Any]] | list[str]) -> None:
        ids = [item if isinstance(item, str) else item["id"] for item in evidence]
        rule_hits.append(
            {"rule_id": rule_id, "flag": flag, "points": points, "evidence_ids": list(dict.fromkeys(ids))}
        )

    # GB-RULE-001: failure burst inside the configured window, 5 points per failure (max 30).
    if len(burst) >= 3:
        hit(
            "GB-RULE-001",
            f"{len(burst)} failed login attempts within {failure_burst_window_minutes}-minute window",
            min(MAX_BURST_POINTS, POINTS_PER_BURST_FAILURE * len(burst)),
            burst,
        )
        # GB-RULE-007: a fast burst (automated guessing) weighs more than a slow one.
        speed, span = _burst_speed_points(burst)
        if speed > 0:
            hit("GB-RULE-007", f"Fast burst: {len(burst)} failures in {span:g} minute(s)", speed, burst)

    # GB-RULE-003: fail-then-success. One hit however many successes follow, so the same
    # failure evidence never inflates the score; each extra success adds a little (max 25).
    if sequence_successes:
        count = len(sequence_successes)
        unfamiliar = [event for event in sequence_successes if event["ip"] not in known_ips]
        label = "unfamiliar" if unfamiliar else "known"
        ips = ", ".join(dict.fromkeys(event["ip"] for event in sequence_successes))
        logins = "successful login" if count == 1 else f"{count} successful login events"
        hit(
            "GB-RULE-003",
            f"Failure burst followed by {logins} from {label} IP {ips}",
            min(MAX_SUCCESS_POINTS, FIRST_SUCCESS_POINTS + EXTRA_SUCCESS_POINTS * (count - 1)),
            sequence_failure_ids + [event["id"] for event in sequence_successes],
        )
        # GB-RULE-008: the attacker-side sign-in used an address this account never uses.
        if unfamiliar:
            hit(
                "GB-RULE-008",
                "Successful login after the burst came from an unfamiliar IP",
                UNFAMILIAR_SUCCESS_POINTS,
                unfamiliar,
            )

    # GB-RULE-002: unfamiliar success alone is informational (0 points) — not automatic
    # proof of malicious activity. Classification becomes INSUFFICIENT_EVIDENCE unless
    # other suspicious rules already fired.
    if unfamiliar_successes and not sequence_successes and len(burst) < 3:
        hit(
            "GB-RULE-002",
            "Successful login from an unfamiliar IP without supporting failure evidence",
            0,
            unfamiliar_successes,
        )

    # GB-RULE-006: longer-term failures outside any burst window (separate from RULE-001).
    if long_horizon_failures:
        hit(
            "GB-RULE-006",
            f"{len(failures)} failed logins observed outside any {failure_burst_window_minutes}-minute burst window",
            0,
            failures,
        )

    suspicious = len(burst) >= 3 or bool(sequence_successes)

    # Context signals only weigh an incident that is already suspicious; on their own they
    # never turn normal or insufficient evidence into a finding.
    if suspicious:
        unfamiliar_ips = list(dict.fromkeys(event["ip"] for event in events if event["ip"] not in known_ips))
        # GB-RULE-009: several unfamiliar addresses involved (4 points per extra IP, max 8).
        if len(unfamiliar_ips) >= 2:
            hit(
                "GB-RULE-009",
                f"{len(unfamiliar_ips)} distinct unfamiliar IPs involved: {', '.join(unfamiliar_ips)}",
                min(MAX_EXTRA_UNFAMILIAR_IP_POINTS, EXTRA_UNFAMILIAR_IP_POINTS * (len(unfamiliar_ips) - 1)),
                [event for event in events if event["ip"] in unfamiliar_ips],
            )

        home = _home_countries(incident, events, known_ips)
        # GB-RULE-010: a sign-in from a country this account has never used.
        new_country = [
            event for event in successes if home and _country(event) not in home | {UNKNOWN_COUNTRY}
        ]
        if new_country:
            countries = ", ".join(dict.fromkeys(_country(event) for event in new_country))
            hit(
                "GB-RULE-010",
                f"Successful login from a new country: {countries} (usual: {', '.join(sorted(home))})",
                NEW_COUNTRY_POINTS,
                new_country,
            )

        # GB-RULE-011: two sign-ins from different countries too close together to travel.
        travel = _impossible_travel(successes)
        if travel:
            earlier, later, minutes = travel
            hit(
                "GB-RULE-011",
                f"Impossible travel: {_country(earlier)} to {_country(later)} in {minutes} minutes",
                IMPOSSIBLE_TRAVEL_POINTS,
                [earlier, later],
            )

        # GB-RULE-012: sign-in at an unusual hour.
        night = [event for event in successes if _parse_event_time(event).hour in OFF_HOURS_UTC]  # type: ignore[union-attr]
        if night:
            hit("GB-RULE-012", "Successful login during off-hours (00:00-05:00 UTC)", OFF_HOURS_POINTS, night)

        # GB-RULE-013: every sign-in came from a known IP in the home country, which lowers
        # the estimate (a forgotten password is the likelier story) but never clears it.
        if sequence_successes and all(
            event["ip"] in known_ips and _country(event) in home | {UNKNOWN_COUNTRY} for event in successes
        ):
            hit(
                "GB-RULE-013",
                "Every successful login came from a known IP in the home country",
                KNOWN_ONLY_POINTS,
                successes,
            )

    # Department never changes the score (former GB-RULE-004 Finance bonus removed; see POL-002).

    score = max(0, min(sum(int(rule["points"]) for rule in rule_hits), 100))

    if suspicious:
        classification = CLASSIFICATION_SUSPICIOUS
        severity: str | None = _severity_for_suspicious(score)
    elif rule_hits:
        classification = CLASSIFICATION_INSUFFICIENT
        severity = None
    else:
        classification = CLASSIFICATION_NORMAL
        severity = None

    evidence_ids = list(
        dict.fromkeys(event_id for rule in rule_hits for event_id in rule["evidence_ids"])
    )

    return {
        "risk_score": score,
        "severity": severity,
        "classification": classification,
        "investigation_priority": _priority_for(classification, severity),
        "rule_hits": rule_hits,
        "flags": [rule["flag"] for rule in rule_hits],
        "evidence_ids": evidence_ids,
        "suggested_action": _suggested_action(classification, severity),
    }
