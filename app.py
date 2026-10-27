"""GuardBee Streamlit MVP - synthetic suspicious-login investigation only."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import streamlit as st

from ai_client import AIReportError, configured_model, generate_report, validate_report_citations
from audit_store import AuditStoreError, get_decision_by_report_id, list_decisions, save_decision
from data_loader import DataValidationError, load_incidents_partitioned, load_policies
from engine import analyze_incident
from retrieval import DEFAULT_MIN_SIMILARITY, retrieve_policies
from ui_presentation import (
    CLASSIFICATION_FILTERS,
    FILTER_ALL,
    FILTER_INSUFFICIENT,
    FILTER_NORMAL,
    FILTER_SUSPICIOUS,
    classification_counts,
    classification_of,
    filter_incidents_by_classification,
    format_severity,
    incident_option_label,
)
from workflow import analysis_context_id, build_decision_record, can_record_decision

ROOT = Path(__file__).parent
st.set_page_config(page_title="GuardBee | Security Decision Copilot", page_icon="🐝", layout="wide")


def read_api_key() -> str:
    """Prefer Streamlit secrets, with an environment variable for local development."""
    try:
        return str(st.secrets.get("NEBIUS_API_KEY", ""))
    except FileNotFoundError:
        return os.getenv("NEBIUS_API_KEY", "")


def read_model() -> str:
    """Allow an account-approved model ID in secrets or the local environment."""
    try:
        return str(st.secrets.get("NEBIUS_MODEL", configured_model()))
    except FileNotFoundError:
        return configured_model()


def reset_investigation_state(incident_id: str) -> None:
    if st.session_state.get("active_incident_id") != incident_id:
        st.session_state.active_incident_id = incident_id
        clear_report_state()


def clear_report_state() -> None:
    """Invalidate a report whenever its incident or analysis context changes."""
    st.session_state.report = None
    st.session_state.report_status = None
    st.session_state.report_context_id = None
    st.session_state.active_report_id = None
    st.session_state.decision = None


def initialize_session() -> None:
    first_load = "audit_hydrated" not in st.session_state
    st.session_state.setdefault("report", None)
    st.session_state.setdefault("report_status", None)
    st.session_state.setdefault("audit", [])
    st.session_state.setdefault("decision", None)
    st.session_state.setdefault("report_context_id", None)
    st.session_state.setdefault("active_report_id", None)
    st.session_state.setdefault("report_sequence", 0)
    st.session_state.setdefault("classification_filter", FILTER_ALL)
    if first_load:
        # Hydrate durable simulated decisions so history survives Streamlit restarts.
        st.session_state.audit = list_decisions()
        st.session_state.audit_hydrated = True


def existing_decision_for_report(report_id: str | None) -> dict[str, Any] | None:
    """Prefer the in-session lock, then any SQLite row for this report ID."""
    session_decision = st.session_state.get("decision")
    if session_decision and report_id and session_decision.get("report_id") == report_id:
        return session_decision
    if not report_id:
        return session_decision
    persisted = get_decision_by_report_id(report_id)
    if persisted:
        st.session_state.decision = persisted
        return persisted
    return session_decision


def audit_decision(
    incident: dict[str, Any],
    decision: str,
    outcome: str,
    current_context_id: str,
    evidence_ids: list[str],
    policy_ids: list[str],
) -> bool:
    """Persist at most one simulated decision for the active validated report."""
    report_id = st.session_state.active_report_id
    record = build_decision_record(
        incident["id"],
        decision,
        outcome,
        st.session_state.report,
        st.session_state.report_context_id,
        current_context_id,
        report_id,
        existing_decision_for_report(report_id),
        evidence_ids=evidence_ids,
        policy_ids=policy_ids,
    )
    if not record:
        return False
    try:
        stored = save_decision(record)
    except AuditStoreError:
        return False
    st.session_state.audit = list_decisions()
    st.session_state.decision = stored
    return True


initialize_session()

st.title("🐝 GuardBee - AI Security Decision Copilot")
st.caption("Synthetic login incidents only • Deterministic detection • Human-approved simulation")
st.info(
    "Demo safety: GuardBee never changes real accounts, sessions, or systems. "
    "Simulated audit decisions persist in a local SQLite file (no secrets stored). "
    "A risk score is not proof of account compromise."
)

try:
    # Scope §1.2: process valid incidents and report invalid ones separately.
    incident_partition = load_incidents_partitioned(ROOT / "data" / "incidents.json")
    incidents = incident_partition.valid
    incident_load_errors = incident_partition.errors
    policies = load_policies(ROOT / "data" / "policies.json")
except DataValidationError as exc:
    st.error("GuardBee could not load its synthetic data safely.")
    st.caption(f"Fix the data file and reload the app: {exc}")
    st.stop()

if incident_load_errors:
    st.warning(
        "Validation excluded one or more incident records. "
        "These are data-quality errors, not security findings."
    )
    for message in incident_load_errors:
        st.caption(message)

if not incidents:
    st.error("No valid incidents remain after validation. Fix the data file and reload.")
    st.stop()

# Detection engine receives only schema-validated incidents.
analyses: dict[str, dict[str, Any]] = {
    incident["id"]: analyze_incident(incident) for incident in incidents
}
counts = classification_counts(analyses)

selected_filter = st.radio(
    "Classification filter",
    options=list(CLASSIFICATION_FILTERS),
    horizontal=True,
    key="classification_filter",
    help=(
        "SUSPICIOUS = investigation-supported patterns. "
        "NORMAL = expected activity (not listed as suspicious). "
        "INSUFFICIENT_EVIDENCE = inconclusive; not confirmed compromise."
    ),
)

filtered_incidents = filter_incidents_by_classification(incidents, analyses, selected_filter)
if not filtered_incidents:
    st.warning(f"No incidents match the {selected_filter} filter. Choose All or another classification.")
    st.stop()

incident_by_id = {incident["id"]: incident for incident in filtered_incidents}
selected_id = st.selectbox(
    "Select a synthetic incident",
    options=list(incident_by_id),
    format_func=lambda identifier: incident_option_label(
        incident_by_id[identifier], analyses[identifier]
    ),
)
incident = incident_by_id[selected_id]
reset_investigation_state(selected_id)
analysis = analyses[incident["id"]]
classification = classification_of(analysis)
severity_label = format_severity(analysis.get("severity"))
priority = analysis.get("investigation_priority", "N/A")

query = " ".join(
    [incident["title"], incident["department"], *analysis["flags"], analysis["suggested_action"]]
)
matched_policies = retrieve_policies(query, policies)
current_context_id = analysis_context_id(incident, analysis, matched_policies)

metrics = st.columns(6)
metrics[0].metric("Total loaded", len(incidents))
metrics[1].metric("Suspicious", counts[FILTER_SUSPICIOUS])
metrics[2].metric("Normal", counts[FILTER_NORMAL])
metrics[3].metric("Insufficient evidence", counts[FILTER_INSUFFICIENT])
metrics[4].metric("Risk score", f"{analysis['risk_score']}/100")
metrics[5].metric("Severity", severity_label)

if classification == FILTER_NORMAL:
    st.success(
        f"Classification: **{classification}** · Investigation priority: **{priority}**. "
        "This activity is not presented as a suspicious incident."
    )
elif classification == FILTER_INSUFFICIENT:
    st.warning(
        f"Classification: **{classification}** · Investigation priority: **{priority}**. "
        "Evidence is inconclusive. This is not confirmed compromise and is not treated as "
        "automatic suspicion from an unfamiliar IP alone."
    )
else:
    st.error(
        f"Classification: **{classification}** · Investigation priority: **{priority}** · "
        f"Severity: **{severity_label}**. Investigate using the evidence below; "
        "a high score is not proof of compromise."
    )

investigate_tab, policy_tab, decision_tab = st.tabs(
    ["Investigate", "Policy retrieval", "Decision & audit"]
)

with investigate_tab:
    st.subheader(f"{incident['id']} - {incident['title']}")
    st.write(
        f"**Synthetic account:** `{incident['account']}`  •  **Department:** {incident['department']}  •  "
        f"**Classification:** `{classification}`  •  **Priority:** `{priority}`  •  "
        f"**Severity:** `{severity_label}`"
    )
    st.subheader("Event timeline")
    st.dataframe(incident["events"], use_container_width=True, hide_index=True)
    st.subheader("Deterministic rule evidence")
    if analysis["rule_hits"]:
        st.dataframe(analysis["rule_hits"], use_container_width=True, hide_index=True)
        if analysis["evidence_ids"]:
            st.caption("Evidence IDs: " + ", ".join(analysis["evidence_ids"]))
        else:
            st.caption("No linked event evidence IDs for informational flags.")
    else:
        st.success("No GuardBee risk rules fired for this synthetic incident.")
    st.caption(f"Suggested action: {analysis['suggested_action']}")

    st.divider()
    st.subheader("Live NVIDIA Nemotron analysis")
    st.caption(f"Nebius Token Factory model: `{read_model()}` (configure an available model for your account).")
    if not matched_policies:
        st.warning(
            "No policy passage met the GuardBee similarity threshold. AI analysis and approval remain unavailable because there is no valid policy context to cite."
        )
    if st.button(
        "Analyze with AI",
        type="primary",
        disabled=not bool(matched_policies),
        use_container_width=True,
    ):
        clear_report_state()
        try:
            with st.spinner("Calling Nebius Token Factory. GuardBee does not fabricate AI reports..."):
                report = generate_report(read_api_key(), incident, analysis, matched_policies, model=read_model())
            usable, reason = validate_report_citations(
                report,
                [event["id"] for event in incident["events"]],
                [policy["id"] for policy in matched_policies],
                classification=analysis.get("classification"),
            )
            if not usable:
                st.session_state.report_status = reason
            else:
                st.session_state.report = report
                st.session_state.report_status = reason
                st.session_state.report_context_id = current_context_id
                st.session_state.report_sequence += 1
                st.session_state.active_report_id = (
                    f"{current_context_id}:{st.session_state.report_sequence}"
                )
        except AIReportError as exc:
            st.session_state.report_status = str(exc)

    if st.session_state.report:
        st.success(st.session_state.report_status)
        st.markdown(st.session_state.report)
    elif st.session_state.report_status:
        st.error(st.session_state.report_status)
        st.caption("Approval remains disabled. Check the key, network access, account credits, and configured model.")
    else:
        st.info("Configure a Nebius API key and request a live report to unlock the human decision controls.")

with policy_tab:
    st.subheader("Relevant sample company policy passages")
    st.caption(
        f"Retrieved locally with scikit-learn TF-IDF cosine similarity. GuardBee shows only matches scoring at least {DEFAULT_MIN_SIMILARITY:.2f}."
    )
    if not matched_policies:
        st.info("No sufficiently relevant sample policy was found for this incident.")
    else:
        for policy in matched_policies:
            with st.expander(f"{policy['id']} - {policy['title']} (similarity {policy['match_score']})", expanded=True):
                st.write(policy["text"])

with decision_tab:
    st.subheader("Human approval gate")
    st.write(f"**Proposed action:** {analysis['suggested_action']}")
    st.caption("This is a demonstration-only simulation. It cannot revoke a session, reset a password, or change a real account.")
    locked_decision = existing_decision_for_report(st.session_state.active_report_id)
    can_decide = can_record_decision(
        st.session_state.report,
        st.session_state.report_context_id,
        current_context_id,
        st.session_state.active_report_id,
        locked_decision,
    )
    if not can_decide:
        if locked_decision:
            st.info("A decision is already recorded for this AI analysis. Run a new analysis to enable one new simulated decision.")
        else:
            st.warning("Approve and Reject unlock only after a current, citation-validated AI report is available.")

    evidence_ids = list(analysis.get("evidence_ids") or [])
    policy_ids = [policy["id"] for policy in matched_policies]
    approve, reject = st.columns(2)
    with approve:
        if st.button("Approve simulated response", disabled=not can_decide, use_container_width=True):
            audit_decision(
                incident,
                "APPROVED",
                "Simulated session-revocation response recorded; no external system was changed.",
                current_context_id,
                evidence_ids,
                policy_ids,
            )
    with reject:
        if st.button("Reject recommendation", disabled=not can_decide, use_container_width=True):
            audit_decision(
                incident,
                "REJECTED",
                "No action taken; recommendation rejected by demo analyst.",
                current_context_id,
                evidence_ids,
                policy_ids,
            )

    if st.session_state.decision:
        st.success(f"{st.session_state.decision['decision']}: {st.session_state.decision['outcome']}")
    st.subheader("Simulated audit history")
    if st.session_state.audit:
        st.dataframe(st.session_state.audit, use_container_width=True, hide_index=True)
    else:
        st.write("No simulated analyst decisions have been recorded yet.")
    st.caption(
        "Audit rows persist in local SQLite across app restarts. Decisions remain simulation-only."
    )
