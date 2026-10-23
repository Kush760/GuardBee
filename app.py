"""GuardBee Streamlit MVP - synthetic suspicious-login investigation only."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import streamlit as st

from ai_client import AIReportError, configured_model, generate_report, validate_report_citations
from data_loader import DataValidationError, load_incidents, load_policies
from engine import analyze_incident
from retrieval import DEFAULT_MIN_SIMILARITY, retrieve_policies
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
    st.session_state.setdefault("report", None)
    st.session_state.setdefault("report_status", None)
    st.session_state.setdefault("audit", [])
    st.session_state.setdefault("decision", None)
    st.session_state.setdefault("report_context_id", None)
    st.session_state.setdefault("active_report_id", None)
    st.session_state.setdefault("report_sequence", 0)


def audit_decision(
    incident: dict[str, Any], decision: str, outcome: str, current_context_id: str
) -> bool:
    """Record at most one simulated decision for the active validated report."""
    record = build_decision_record(
        incident["id"],
        decision,
        outcome,
        st.session_state.report,
        st.session_state.report_context_id,
        current_context_id,
        st.session_state.active_report_id,
        st.session_state.decision,
    )
    if not record:
        return False
    st.session_state.audit.append(record)
    st.session_state.decision = record
    return True


initialize_session()

st.title("🐝 GuardBee - AI Security Decision Copilot")
st.caption("Synthetic login incidents only • Deterministic detection • Human-approved simulation")
st.info("Demo safety: GuardBee never changes real accounts, sessions, or systems. Audit history is temporary to this browser session.")

try:
    incidents = load_incidents(ROOT / "data" / "incidents.json")
    policies = load_policies(ROOT / "data" / "policies.json")
except DataValidationError as exc:
    st.error("GuardBee could not load its synthetic data safely.")
    st.caption(f"Fix the data file and reload the app: {exc}")
    st.stop()

incident_by_id = {incident["id"]: incident for incident in incidents}
selected_id = st.selectbox(
    "Select a synthetic incident",
    options=list(incident_by_id),
    format_func=lambda identifier: f"{identifier} - {incident_by_id[identifier]['title']}",
)
incident = incident_by_id[selected_id]
reset_investigation_state(selected_id)
analysis = analyze_incident(incident)
query = " ".join(
    [incident["title"], incident["department"], *analysis["flags"], analysis["suggested_action"]]
)
matched_policies = retrieve_policies(query, policies)
current_context_id = analysis_context_id(incident, analysis, matched_policies)

metrics = st.columns(4)
metrics[0].metric("Synthetic incidents", len(incidents))
metrics[1].metric("Deterministic risk", f"{analysis['risk_score']}/100")
metrics[2].metric("Severity", analysis["severity"])
metrics[3].metric("Evidence events", len(analysis["evidence_ids"]))

investigate_tab, policy_tab, decision_tab = st.tabs(
    ["Investigate", "Policy retrieval", "Decision & audit"]
)

with investigate_tab:
    st.subheader(f"{incident['id']} - {incident['title']}")
    st.write(f"**Synthetic account:** `{incident['account']}`  •  **Department:** {incident['department']}")
    st.subheader("Event timeline")
    st.dataframe(incident["events"], use_container_width=True, hide_index=True)
    st.subheader("Deterministic rule evidence")
    if analysis["rule_hits"]:
        st.dataframe(analysis["rule_hits"], use_container_width=True, hide_index=True)
        st.caption("Evidence IDs: " + ", ".join(analysis["evidence_ids"]))
    else:
        st.success("No GuardBee risk rules fired for this synthetic incident.")

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
    can_decide = can_record_decision(
        st.session_state.report,
        st.session_state.report_context_id,
        current_context_id,
        st.session_state.active_report_id,
        st.session_state.decision,
    )
    if not can_decide:
        if st.session_state.decision:
            st.info("A decision is already recorded for this AI analysis. Run a new analysis to enable one new simulated decision.")
        else:
            st.warning("Approve and Reject unlock only after a current, citation-validated AI report is available.")

    approve, reject = st.columns(2)
    with approve:
        if st.button("Approve simulated response", disabled=not can_decide, use_container_width=True):
            audit_decision(
                incident,
                "APPROVED",
                "Simulated session-revocation response recorded; no external system was changed.",
                current_context_id,
            )
    with reject:
        if st.button("Reject recommendation", disabled=not can_decide, use_container_width=True):
            audit_decision(
                incident,
                "REJECTED",
                "No action taken; recommendation rejected by demo analyst.",
                current_context_id,
            )

    if st.session_state.decision:
        st.success(f"{st.session_state.decision['decision']}: {st.session_state.decision['outcome']}")
    st.subheader("Temporary session audit history")
    if st.session_state.audit:
        st.dataframe(st.session_state.audit, use_container_width=True, hide_index=True)
    else:
        st.write("No analyst decisions have been recorded in this session.")
    st.caption("This in-memory audit history resets when the Streamlit session ends or refreshes.")
