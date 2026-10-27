"""Validated loading for GuardBee's synthetic JSON data files."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Iterator


class DataValidationError(ValueError):
    """Raised when a synthetic GuardBee data file is missing or invalid."""


@dataclass(frozen=True)
class IncidentValidationIssue:
    """One explicitly reported invalid incident record (never silently dropped)."""

    index: int
    message: str
    incident_id: str | None = None

    def as_text(self) -> str:
        if self.incident_id:
            return f"{self.message} (incident_id={self.incident_id!r})"
        return self.message


@dataclass(frozen=True)
class IncidentPartitionResult:
    """Deterministic partition of an incident collection.

    Unpack as ``valid, errors = result`` for compatibility with older callers.
    Prefer ``result.valid`` / ``result.issues`` for structured consumers.
    """

    valid: list[dict[str, Any]]
    issues: list[IncidentValidationIssue]

    @property
    def errors(self) -> list[str]:
        return [issue.as_text() for issue in self.issues]

    def __iter__(self) -> Iterator[Any]:
        yield self.valid
        yield self.errors


def _require_string(value: Any, field: str, context: str) -> None:
    if not isinstance(value, str) or not value.strip():
        if field == "ip" and isinstance(value, str) and not value.strip():
            raise DataValidationError(
                f"{context}.ip must be a non-empty string "
                "(empty IP is invalid and must not be treated as an unfamiliar address)."
            )
        raise DataValidationError(f"{context}.{field} must be a non-empty string.")


def _require_unique_ids(items: list[dict[str, Any]], context: str) -> None:
    identifiers = [item["id"] for item in items]
    if len(identifiers) != len(set(identifiers)):
        raise DataValidationError(f"{context} contains duplicate id values.")


def _incident_id_hint(incident: Any) -> str | None:
    if isinstance(incident, dict):
        identifier = incident.get("id")
        if isinstance(identifier, str) and identifier.strip():
            return identifier
    return None


def _validate_event(event: Any, context: str) -> None:
    if not isinstance(event, dict):
        raise DataValidationError(f"{context} must be an object.")
    for field in ("id", "time_utc", "type", "ip", "country"):
        _require_string(event.get(field), field, context)
    if event["type"] not in {"login_failed", "login_success"}:
        raise DataValidationError(f"{context}.type must be login_failed or login_success.")
    try:
        datetime.fromisoformat(event["time_utc"].replace("Z", "+00:00"))
    except ValueError as exc:
        raise DataValidationError(f"{context}.time_utc must be an ISO-8601 timestamp.") from exc


def _validate_incident_object(incident: Any, context: str) -> None:
    """Raise DataValidationError when a single incident record is invalid."""
    if not isinstance(incident, dict):
        raise DataValidationError(f"{context} must be an object.")
    for field in ("id", "title", "account", "department"):
        _require_string(incident.get(field), field, context)
    known_ips = incident.get("known_ips")
    if not isinstance(known_ips, list) or not all(
        isinstance(ip, str) and ip.strip() for ip in known_ips
    ):
        raise DataValidationError(f"{context}.known_ips must be an array of non-empty strings.")
    events = incident.get("events")
    if not isinstance(events, list) or not events:
        raise DataValidationError(f"{context}.events must be a non-empty array.")
    for event_index, event in enumerate(events):
        _validate_event(event, f"{context}.events[{event_index}]")
    _require_unique_ids(events, f"{context}.events")


def partition_incidents(value: Any) -> IncidentPartitionResult:
    """Validate incident records individually.

    Returns an ``IncidentPartitionResult`` with ``valid`` records and explicit
    ``issues`` for every rejected record. Invalid records are never silently
    dropped. Duplicate incident IDs among otherwise valid records are reported
    and excluded from the valid list (first occurrence kept).

    File-level failures (empty collection, non-list root) raise
    ``DataValidationError`` and are not represented as per-record issues.
    """
    if not isinstance(value, list) or not value:
        raise DataValidationError("Incident data must be a non-empty JSON array.")

    valid: list[dict[str, Any]] = []
    issues: list[IncidentValidationIssue] = []
    seen_ids: set[str] = set()

    for index, incident in enumerate(value):
        context = f"incidents[{index}]"
        incident_id = _incident_id_hint(incident)
        try:
            _validate_incident_object(incident, context)
        except DataValidationError as exc:
            issues.append(
                IncidentValidationIssue(
                    index=index, message=str(exc), incident_id=incident_id
                )
            )
            continue
        incident_id = incident["id"]
        if incident_id in seen_ids:
            issues.append(
                IncidentValidationIssue(
                    index=index,
                    message=f"{context} duplicates incident id {incident_id!r}.",
                    incident_id=incident_id,
                )
            )
            continue
        seen_ids.add(incident_id)
        valid.append(incident)

    return IncidentPartitionResult(valid=valid, issues=issues)


def validate_incidents(value: Any) -> list[dict[str, Any]]:
    """Validate the documented synthetic incident collection format.

    Fail-closed: any invalid record raises ``DataValidationError``. Prefer
    ``partition_incidents`` when callers need to process valid rows and report
    invalid ones separately.
    """
    result = partition_incidents(value)
    if result.issues:
        raise DataValidationError(" ".join(result.errors))
    return result.valid


def validate_policies(value: Any) -> list[dict[str, Any]]:
    """Validate the documented sample policy collection format.

    Required fields: ``id``, ``title``, ``text``.
    Optional enrichment (MVP Scope §5): ``description``, ``categories``,
    ``conditions``, ``investigation_guidance``. Missing optionals are allowed;
    present optionals must use the documented types.
    """
    if not isinstance(value, list) or not value:
        raise DataValidationError("Policy data must be a non-empty JSON array.")
    for index, policy in enumerate(value):
        context = f"policies[{index}]"
        if not isinstance(policy, dict):
            raise DataValidationError(f"{context} must be an object.")
        for field in ("id", "title", "text"):
            _require_string(policy.get(field), field, context)
        for optional_string in ("description", "conditions", "investigation_guidance"):
            if optional_string in policy and policy[optional_string] is not None:
                if not isinstance(policy[optional_string], str) or not policy[optional_string].strip():
                    raise DataValidationError(
                        f"{context}.{optional_string} must be a non-empty string when provided."
                    )
        if "categories" in policy and policy["categories"] is not None:
            categories = policy["categories"]
            if not isinstance(categories, list) or not all(
                isinstance(item, str) and item.strip() for item in categories
            ):
                raise DataValidationError(
                    f"{context}.categories must be an array of non-empty strings when provided."
                )
    _require_unique_ids(value, "Policy data")
    return value


def _load_collection(
    path: Path, validator: Callable[[Any], list[dict[str, Any]]], label: str
) -> list[dict[str, Any]]:
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise DataValidationError(f"Could not read {label} file: {path.name}.") from exc
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise DataValidationError(f"{label} file {path.name} is not valid JSON.") from exc
    return validator(parsed)


def load_incidents(path: Path) -> list[dict[str, Any]]:
    """Load incidents with fail-closed validation (all-or-nothing)."""
    return _load_collection(path, validate_incidents, "Incident data")


def load_incidents_partitioned(path: Path) -> IncidentPartitionResult:
    """Load incidents, returning valid records plus explicit per-record issues.

    Missing files and malformed JSON remain hard ``DataValidationError`` failures
    (not silent empties). Mixed valid/invalid arrays are partitioned.
    """
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise DataValidationError(f"Could not read Incident data file: {path.name}.") from exc
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise DataValidationError(f"Incident data file {path.name} is not valid JSON.") from exc
    return partition_incidents(parsed)


def load_policies(path: Path) -> list[dict[str, Any]]:
    return _load_collection(path, validate_policies, "Policy data")
