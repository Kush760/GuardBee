"""Validated loading for GuardBee's synthetic JSON data files."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Callable


class DataValidationError(ValueError):
    """Raised when a synthetic GuardBee data file is missing or invalid."""


def _require_string(value: Any, field: str, context: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise DataValidationError(f"{context}.{field} must be a non-empty string.")


def _require_unique_ids(items: list[dict[str, Any]], context: str) -> None:
    identifiers = [item["id"] for item in items]
    if len(identifiers) != len(set(identifiers)):
        raise DataValidationError(f"{context} contains duplicate id values.")


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


def validate_incidents(value: Any) -> list[dict[str, Any]]:
    """Validate the documented synthetic incident collection format."""
    if not isinstance(value, list) or not value:
        raise DataValidationError("Incident data must be a non-empty JSON array.")
    for index, incident in enumerate(value):
        context = f"incidents[{index}]"
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
    _require_unique_ids(value, "Incident data")
    return value


def validate_policies(value: Any) -> list[dict[str, Any]]:
    """Validate the documented sample policy collection format."""
    if not isinstance(value, list) or not value:
        raise DataValidationError("Policy data must be a non-empty JSON array.")
    for index, policy in enumerate(value):
        context = f"policies[{index}]"
        if not isinstance(policy, dict):
            raise DataValidationError(f"{context} must be an object.")
        for field in ("id", "title", "text"):
            _require_string(policy.get(field), field, context)
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
    return _load_collection(path, validate_incidents, "Incident data")


def load_policies(path: Path) -> list[dict[str, Any]]:
    return _load_collection(path, validate_policies, "Policy data")
