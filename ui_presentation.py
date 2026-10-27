"""Pure presentation helpers for GuardBee Streamlit UI (no Streamlit import)."""

from __future__ import annotations

from typing import Any

FILTER_ALL = "All"
FILTER_SUSPICIOUS = "SUSPICIOUS"
FILTER_NORMAL = "NORMAL"
FILTER_INSUFFICIENT = "INSUFFICIENT_EVIDENCE"

CLASSIFICATION_FILTERS = (
    FILTER_ALL,
    FILTER_SUSPICIOUS,
    FILTER_NORMAL,
    FILTER_INSUFFICIENT,
)


def format_severity(severity: str | None) -> str:
    """Show severity only when the backend provides one; never render None as a band."""
    if severity in {"HIGH", "MEDIUM", "LOW"}:
        return severity
    return "N/A"


def classification_of(analysis: dict[str, Any]) -> str:
    """Read backend classification with a safe fallback for unexpected payloads."""
    value = analysis.get("classification")
    if value in {FILTER_SUSPICIOUS, FILTER_NORMAL, FILTER_INSUFFICIENT}:
        return value
    return FILTER_INSUFFICIENT


def matches_classification_filter(classification: str, selected_filter: str) -> bool:
    if selected_filter == FILTER_ALL:
        return True
    return classification == selected_filter


def filter_incidents_by_classification(
    incidents: list[dict[str, Any]],
    analyses: dict[str, dict[str, Any]],
    selected_filter: str,
) -> list[dict[str, Any]]:
    """Return incidents whose backend classification matches the UI filter."""
    matched: list[dict[str, Any]] = []
    for incident in incidents:
        analysis = analyses[incident["id"]]
        if matches_classification_filter(classification_of(analysis), selected_filter):
            matched.append(incident)
    return matched


def classification_counts(analyses: dict[str, dict[str, Any]]) -> dict[str, int]:
    counts = {
        FILTER_SUSPICIOUS: 0,
        FILTER_NORMAL: 0,
        FILTER_INSUFFICIENT: 0,
    }
    for analysis in analyses.values():
        label = classification_of(analysis)
        if label in counts:
            counts[label] += 1
    return counts


def incident_option_label(incident: dict[str, Any], analysis: dict[str, Any]) -> str:
    """Selectbox label that states classification explicitly (avoids implying suspicion)."""
    return (
        f"{incident['id']} [{classification_of(analysis)}] - {incident['title']}"
    )
