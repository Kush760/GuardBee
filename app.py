"""GuardBee Streamlit MVP - synthetic suspicious-login investigation only.

Three native-Streamlit pages: Dashboard, Security Incidents, and Audit History.
Risk facts come from engine.py, policies from retrieval.py, AI text from
ai_client.py, and decision gates from workflow.py; this module only presents
them. Dynamic text is shown in plain-text widgets (tables, metrics) or is
Markdown-escaped first. No raw HTML is rendered.
"""

from __future__ import annotations

import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any

import streamlit as st

from ai_client import (
    AIReportError,
    configured_model,
    extract_citation_ids,
    generate_report,
    validate_report_citations,
)
from data_loader import DataValidationError, load_incidents, load_policies
from engine import analyze_incident
from retrieval import DEFAULT_MIN_SIMILARITY, retrieve_policies
from workflow import analysis_context_id, build_decision_record, can_record_decision

ROOT = Path(__file__).parent
st.set_page_config(page_title="GuardBee | Security Decision Copilot", page_icon="🐝", layout="wide")

PAGES = ("Dashboard", "Security Incidents", "Audit History")

# Wording required by the UI specification. The class itself must come from engine.py;
# the UI never infers one from the score or severity.
CLASSIFICATIONS = {
    "SUSPICIOUS": ("red", "The available events match one or more configured suspicious patterns."),
    "INSUFFICIENT_EVIDENCE": (
        "orange",
        "The available evidence is not sufficient to classify this activity as normal or suspicious.",
    ),
    "NORMAL": ("green", "No suspicious pattern was detected by the configured rules in the available events."),
}
SEVERITY_COLORS = {"HIGH": "red", "MEDIUM": "orange", "LOW": "blue"}
NOT_ASSIGNED = "Not assigned"
RISK_NOTE = (
    "The risk score (0–100) and severity estimate investigation risk from synthetic evidence. "
    "A high score is not proof of compromise."
)
UNKNOWNS = (
    "Whether the account owner made these logins; the data does not verify identity.",
    "Device, browser, and VPN details; they are not present in the data.",
    "Any activity outside this synthetic event set.",
)
STEP_MARKS = {"done": ":green[✔]", "active": ":orange[●]", "locked": ":gray[○]", "blocked": ":red[✖]"}

_MARKDOWN_SPECIAL = re.compile(r"([\\`*_{}\[\]()#+\-.!|<>~$:])")


def md(value: Any) -> str:
    """Escape Markdown so data text is always shown literally."""
    return _MARKDOWN_SPECIAL.sub(r"\\\1", str(value))


# ---------------------------------------------------------------------------
# Configuration and session state
# ---------------------------------------------------------------------------
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


def initialize_session() -> None:
    st.session_state.setdefault("report", None)
    st.session_state.setdefault("report_status", None)
    st.session_state.setdefault("audit", [])
    st.session_state.setdefault("decision", None)
    st.session_state.setdefault("report_context_id", None)
    st.session_state.setdefault("active_report_id", None)
    st.session_state.setdefault("report_sequence", 0)
    st.session_state.setdefault("current_incident_id", None)


def clear_report_state() -> None:
    """Invalidate a report whenever its incident or analysis context changes."""
    st.session_state.report = None
    st.session_state.report_status = None
    st.session_state.report_context_id = None
    st.session_state.active_report_id = None
    st.session_state.decision = None


def reset_investigation_state(incident_id: str) -> None:
    if st.session_state.get("active_incident_id") != incident_id:
        st.session_state.active_incident_id = incident_id
        clear_report_state()


def open_incident(incident_id: str) -> None:
    """Button callback: show one incident on the Security Incidents page."""
    st.session_state.page = "Security Incidents"
    st.session_state.incident_filter = "All"
    st.session_state.current_incident_id = incident_id


def sync_incident_picker() -> None:
    st.session_state.current_incident_id = st.session_state.incident_picker


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


def run_ai_analysis(
    incident: dict[str, Any],
    analysis: dict[str, Any],
    matched_policies: list[dict[str, Any]],
    current_context_id: str,
) -> None:
    """Request a report and keep it only if its citations validate; never fabricate one."""
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
            st.session_state.active_report_id = f"{current_context_id}:{st.session_state.report_sequence}"
    except AIReportError as exc:
        st.session_state.report_status = str(exc)


# ---------------------------------------------------------------------------
# Presentation helpers (read engine output; never compute risk facts)
# ---------------------------------------------------------------------------
def classification_of(analysis: dict[str, Any]) -> str | None:
    value = analysis.get("classification")
    return value if value in CLASSIFICATIONS else None


def classification_text(analysis: dict[str, Any]) -> str:
    value = classification_of(analysis)
    return value.replace("_", " ") if value else "Not classified"


def severity_text(analysis: dict[str, Any]) -> str:
    return analysis.get("severity") or NOT_ASSIGNED


def priority_text(analysis: dict[str, Any]) -> str:
    return analysis.get("investigation_priority") or "Not provided"


def severity_markdown(analysis: dict[str, Any]) -> str:
    severity = analysis.get("severity")
    if severity in SEVERITY_COLORS:
        return f":{SEVERITY_COLORS[severity]}-background[{severity}]"
    return md(severity_text(analysis))


def overview_rows(incidents: list[dict[str, Any]], analyses: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "Incident": incident["id"],
            "Title": incident["title"],
            "Classification": classification_text(analyses[incident["id"]]),
            "Risk score": analyses[incident["id"]]["risk_score"],
            "Severity": severity_text(analyses[incident["id"]]),
            "Investigation priority": priority_text(analyses[incident["id"]]),
            "Events": len(incident["events"]),
        }
        for incident in incidents
    ]


OVERVIEW_COLUMNS = {
    "Risk score": st.column_config.ProgressColumn(
        "Risk score", min_value=0, max_value=100, format="%d", help=RISK_NOTE
    ),
}


def event_time(event: dict[str, Any]) -> datetime:
    return datetime.fromisoformat(event["time_utc"].replace("Z", "+00:00"))


# ---------------------------------------------------------------------------
# Data
# ---------------------------------------------------------------------------
initialize_session()

try:
    incidents = load_incidents(ROOT / "data" / "incidents.json")
    policies = load_policies(ROOT / "data" / "policies.json")
except DataValidationError as exc:
    st.title("🐝 GuardBee")
    st.error("GuardBee could not load its synthetic data safely, so no incidents or counts are shown.")
    st.caption(f"Fix the data file and reload the app: {md(exc)}")
    st.stop()

incident_by_id = {incident["id"]: incident for incident in incidents}
analyses = {incident["id"]: analyze_incident(incident) for incident in incidents}
any_classified = any(classification_of(analysis) for analysis in analyses.values())
if st.session_state.current_incident_id not in incident_by_id:
    st.session_state.current_incident_id = incidents[0]["id"]

# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------
with st.sidebar:
    st.title("🐝 GuardBee")
    st.caption("AI security decision copilot · synthetic demo")
    page = st.radio("Go to", PAGES, key="page")
    st.divider()
    st.markdown("**AI provider**")
    if read_api_key():
        st.success("Nebius API key configured", icon="🔑")
    else:
        st.warning("No Nebius API key configured. AI explanations will show an error.", icon="🔑")
    st.caption(f"Model: {md(read_model())}")
    st.caption(f"Simulated decisions this session: {len(st.session_state.audit)}")
    st.info(
        "Demo only: synthetic incidents and simulated decisions. GuardBee does not monitor live systems "
        "or change any account.",
        icon="🛡️",
    )


# ---------------------------------------------------------------------------
# Page A - Dashboard
# ---------------------------------------------------------------------------
def dashboard_page() -> None:
    st.title("Dashboard")
    st.caption(
        "Overview of the static synthetic dataset in `data/incidents.json`. This is not live monitoring."
    )

    columns = st.columns(4)
    columns[0].metric("Valid incidents loaded", len(incidents))
    if any_classified:
        for column, key in zip(columns[1:], CLASSIFICATIONS):
            count = sum(1 for analysis in analyses.values() if classification_of(analysis) == key)
            column.metric(key.replace("_", " ").title(), count)
    else:
        columns[1].metric("Suspicious", "—")
        columns[2].metric("Insufficient evidence", "—")
        columns[3].metric("Normal", "—")
        st.info(
            "Classification counts are unavailable: `engine.py` does not return a classification yet. "
            "GuardBee does not infer one from the risk score.",
            icon="ℹ️",
        )

    severity_columns = st.columns(4)
    for column, label in zip(severity_columns, ("HIGH", "MEDIUM", "LOW", None)):
        count = sum(1 for analysis in analyses.values() if analysis.get("severity") == label)
        column.metric(f"Severity {label.title() if label else NOT_ASSIGNED.lower()}", count)
    st.caption(RISK_NOTE)
    st.caption(
        "Data validation is fail-closed: every record must pass validation or loading stops. "
        "Partial processing of valid records is not implemented yet."
    )

    st.subheader("Incident overview")
    st.dataframe(
        overview_rows(incidents, analyses),
        hide_index=True,
        column_config=OVERVIEW_COLUMNS,
    )
    pick, action = st.columns([3, 1], vertical_alignment="bottom")
    chosen = pick.selectbox(
        "Open an incident",
        list(incident_by_id),
        format_func=lambda identifier: f"{identifier} · {incident_by_id[identifier]['title']}",
        key="dashboard_pick",
    )
    action.button("Open in Security Incidents", key="dashboard_open", on_click=open_incident, args=(chosen,))


# ---------------------------------------------------------------------------
# Page B - Security Incidents
# ---------------------------------------------------------------------------
def render_stepper(slot: Any, steps: list[tuple[str, str, str]]) -> None:
    with slot:
        for column, (index, (title, state, detail)) in zip(st.columns(len(steps)), enumerate(steps, 1)):
            column.markdown(f"{STEP_MARKS[state]} **{index} · {title}**")
            column.caption(detail)


def render_incident(incident: dict[str, Any]) -> None:
    reset_investigation_state(incident["id"])
    analysis = analyses[incident["id"]]
    query = " ".join(
        [incident["title"], incident["department"], *analysis["flags"], analysis["suggested_action"]]
    )
    matched_policies = retrieve_policies(query, policies)
    current_context_id = analysis_context_id(incident, analysis, matched_policies)

    st.subheader(md(f"{incident['id']} · {incident['title']}"))
    known_ips = ", ".join(incident.get("known_ips", [])) or "none listed"
    st.caption(
        md(f"Account: {incident['account']}  ·  Department: {incident['department']}  ·  Known IPs: {known_ips}")
    )

    with st.container(border=True):
        classification = classification_of(analysis)
        if classification:
            color, wording = CLASSIFICATIONS[classification]
            st.markdown(f"**Classification:** :{color}-background[{classification.replace('_', ' ')}]")
            st.caption(wording)
        else:
            st.markdown("**Classification:** :gray-background[NOT CLASSIFIED]")
            st.caption(
                "`engine.py` does not provide a classification yet. A low or zero score alone does not "
                "show that this activity is normal."
            )

    metrics = st.columns(4)
    metrics[0].metric("Risk score", f"{analysis['risk_score']} / 100", help=RISK_NOTE)
    metrics[1].metric("Severity", severity_text(analysis))
    metrics[2].metric("Investigation priority", priority_text(analysis))
    metrics[3].metric("Evidence events", len(analysis["evidence_ids"]))
    st.caption(RISK_NOTE)

    stepper = st.container(border=True)

    # -- Deterministic engine results ---------------------------------------
    st.subheader("Engine analysis")
    st.caption("Deterministic rules in `engine.py`. No AI is used to establish these results.")
    evidence = set(analysis["evidence_ids"])
    known = set(incident.get("known_ips", []))
    with st.expander(f"Event timeline · {len(incident['events'])} events, oldest first", expanded=True):
        st.dataframe(
            [
                {
                    "Event": event["id"],
                    "Time (UTC)": event["time_utc"],
                    "Type": event["type"],
                    "IP": event["ip"],
                    "IP status": "Known" if event["ip"] in known else "Unfamiliar",
                    "Country": event.get("country", ""),
                    "Rule evidence": event["id"] in evidence,
                }
                for event in sorted(incident["events"], key=event_time)
            ],
            hide_index=True,
        )
    with st.expander(f"Triggered rules · {len(analysis['rule_hits'])}", expanded=True):
        if analysis["rule_hits"]:
            st.dataframe(
                [
                    {
                        "Rule": hit["rule_id"],
                        "Finding": hit["flag"],
                        "Points": hit["points"],
                        "Evidence events": ", ".join(hit["evidence_ids"]) or "Account context",
                    }
                    for hit in analysis["rule_hits"]
                ],
                hide_index=True,
            )
            total = sum(hit["points"] for hit in analysis["rule_hits"])
            st.caption(f"Rule points total {total}; the risk score is capped at 100.")
        else:
            st.info("No configured rule matched the available events.")
    with st.expander("Observed facts, interpretation, and unknowns"):
        events = incident["events"]
        failed = sum(1 for event in events if event["type"] == "login_failed")
        unfamiliar = sorted({event["ip"] for event in events if event["ip"] not in known})
        st.markdown("**Observed in the events**")
        st.markdown(
            md(
                f"{failed} failed and {len(events) - failed} successful login events "
                f"from {len({event['ip'] for event in events})} IP address(es)."
            )
        )
        st.markdown(
            md(f"IPs not in the known-IP list: {', '.join(unfamiliar)}.")
            if unfamiliar
            else "All events came from known IPs."
        )
        st.markdown("**Engine interpretation**")
        for flag in analysis["flags"] or ["No configured rule matched."]:
            st.markdown(f"- {md(flag)}")
        st.markdown("**Unknown from this data**")
        for unknown in UNKNOWNS:
            st.markdown(f"- {md(unknown)}")

    # -- Policies --------------------------------------------------------------
    st.subheader("Relevant policies")
    st.caption(
        f"Retrieved locally with TF-IDF cosine similarity from `data/policies.json`. "
        f"Only passages scoring at least {DEFAULT_MIN_SIMILARITY:.2f} are shown."
    )
    if matched_policies:
        for index, policy in enumerate(matched_policies):
            label = f"{policy['id']} · {policy['title']} · similarity {policy['match_score']:.3f}"
            with st.expander(md(label), expanded=index == 0):
                st.markdown(md(policy["text"]))
    else:
        st.warning(
            "No policy passage met the similarity threshold. AI explanation and decisions are unavailable "
            "without policy context to cite."
        )

    # -- AI explanation ---------------------------------------------------------
    st.subheader("AI explanation")
    with st.container(border=True):
        st.caption(
            f"AI-generated · NVIDIA Nemotron via Nebius Token Factory · model {md(read_model())}. "
            "Separate from the deterministic engine results above."
        )
        if st.button(
            "Generate AI explanation",
            type="primary",
            key="ai_request_btn",
            disabled=not matched_policies,
        ):
            run_ai_analysis(incident, analysis, matched_policies, current_context_id)

        if st.session_state.report:
            st.success(md(st.session_state.report_status), icon="✅")
            cited_events, cited_policies = extract_citation_ids(st.session_state.report)
            titles = {policy["id"].upper(): policy["title"] for policy in matched_policies}
            st.markdown("**Cited evidence:** " + " ".join(f"`{event_id}`" for event_id in cited_events))
            st.markdown(
                "**Cited policies:** "
                + "; ".join(f"`{policy_id}` {md(titles.get(policy_id, ''))}" for policy_id in cited_policies)
            )
            st.caption(
                "Each cited ID was checked against this incident's events and the retrieved policies. "
                "That does not prove every sentence; treat inferred risk and unknowns as unconfirmed."
            )
            with st.container(border=True):
                st.markdown(st.session_state.report)
        elif st.session_state.report_status:
            st.error(md(st.session_state.report_status))
            st.caption(
                "No explanation was generated or substituted. Check the API key, network access, account "
                "credits, and configured model, then retry."
            )
            if st.button("Retry AI explanation", key="ai_retry_btn", disabled=not matched_policies):
                run_ai_analysis(incident, analysis, matched_policies, current_context_id)
                st.rerun()
        elif matched_policies:
            st.info("Generate an AI explanation to unlock the simulated decision. A Nebius API key is required.")

    # -- Simulated decision -----------------------------------------------------------
    st.subheader("Simulated decision")
    can_decide = can_record_decision(
        st.session_state.report,
        st.session_state.report_context_id,
        current_context_id,
        st.session_state.active_report_id,
        st.session_state.decision,
    )
    with st.container(border=True):
        st.markdown(f"**Proposed simulated action:** {md(analysis['suggested_action'])}")
        st.caption("Simulation only. GuardBee cannot block accounts, revoke sessions, or change any system.")
        decision = st.session_state.decision
        if decision:
            st.success(
                md(f"{decision['decision']} recorded at {decision['time_utc']} (UTC): {decision['outcome']}"),
                icon="📝",
            )
            st.caption("A decision is already recorded for this report. Generate a new explanation to decide again.")
        elif not st.session_state.report:
            st.warning("Locked: generate a citation-validated AI explanation first.", icon="🔒")
        elif not can_decide:
            st.warning(
                "Locked: the AI report belongs to a different incident or analysis context. "
                "Generate a new explanation.",
                icon="🔒",
            )
        approve, reject = st.columns(2)
        for column, label, key, verdict, outcome in (
            (approve, "Approve (simulated)", "btn_approve", "APPROVED",
             "Simulated session-revocation response recorded; no external system was changed."),
            (reject, "Reject (simulated)", "btn_reject", "REJECTED",
             "No action taken; recommendation rejected by demo analyst."),
        ):
            if column.button(label, key=key, disabled=not can_decide, use_container_width=True):
                if audit_decision(incident, verdict, outcome, current_context_id):
                    st.rerun()
                st.error("The decision was not recorded: the report is no longer valid for this context.")

    if st.session_state.report:
        ai_step = ("AI explanation", "done", "Citations validated")
    elif st.session_state.report_status:
        ai_step = ("AI explanation", "blocked", "Not usable")
    elif matched_policies:
        ai_step = ("AI explanation", "active", "Ready to generate")
    else:
        ai_step = ("AI explanation", "locked", "Needs policy context")
    if st.session_state.decision:
        decision_step = ("Decision", "done", st.session_state.decision["decision"].title())
    elif can_decide:
        decision_step = ("Decision", "active", "Awaiting analyst")
    else:
        decision_step = ("Decision", "locked", "Needs validated report")
    render_stepper(
        stepper,
        [
            ("Detect", "done", f"Score {analysis['risk_score']}/100"),
            ("Evidence", "done", f"{len(analysis['evidence_ids'])} evidence event(s)"),
            (
                "Policy",
                "done" if matched_policies else "blocked",
                f"{len(matched_policies)} matched" if matched_policies else "No match",
            ),
            ai_step,
            decision_step,
        ],
    )


def incidents_page() -> None:
    st.title("Security Incidents")
    st.caption(RISK_NOTE)

    filters = {"All": None, "High": "HIGH", "Medium": "MEDIUM", "Low": "LOW"}
    if any_classified:
        filters.update({key.replace("_", " ").title(): key for key in CLASSIFICATIONS})
    choice = st.radio("Filter", list(filters), horizontal=True, key="incident_filter")
    wanted = filters[choice]
    shown = [
        incident
        for incident in incidents
        if wanted is None
        or analyses[incident["id"]].get("severity") == wanted
        or classification_of(analyses[incident["id"]]) == wanted
    ]
    if not shown:
        st.info("No incidents match this filter.")
        return
    st.dataframe(overview_rows(shown, analyses), hide_index=True, column_config=OVERVIEW_COLUMNS)

    shown_ids = [incident["id"] for incident in shown]
    if st.session_state.current_incident_id not in shown_ids:
        st.session_state.current_incident_id = shown_ids[0]
    st.session_state.incident_picker = st.session_state.current_incident_id
    selected = st.selectbox(
        "Investigate incident",
        shown_ids,
        format_func=lambda identifier: (
            f"{identifier} · {incident_by_id[identifier]['title']} · score {analyses[identifier]['risk_score']}"
        ),
        key="incident_picker",
        on_change=sync_incident_picker,
    )
    st.divider()
    render_incident(incident_by_id[selected])


# ---------------------------------------------------------------------------
# Page C - Audit History
# ---------------------------------------------------------------------------
def audit_page() -> None:
    st.title("Audit History")
    st.warning(
        "Session-only storage: persistent SQLite audit storage is not implemented yet, so these records "
        "disappear when the browser session ends or the app restarts.",
        icon="⚠️",
    )
    records = st.session_state.audit
    if not records:
        st.info("No simulated decisions have been recorded in this session yet.")
        return
    st.dataframe(
        [
            {
                "Time (UTC)": record["time_utc"],
                "Incident": record["incident_id"],
                "Decision": record["decision"],
                "Simulation only": record["simulation_only"],
                "Actor": record["actor"],
                "Outcome": record["outcome"],
                "Report reference": record["report_id"],
            }
            for record in reversed(records)
        ],
        hide_index=True,
    )
    decided = list(dict.fromkeys(record["incident_id"] for record in reversed(records)))
    pick, action = st.columns([3, 1], vertical_alignment="bottom")
    chosen = pick.selectbox("Open an incident from the history", decided, key="audit_pick")
    action.button("Open in Security Incidents", key="audit_open", on_click=open_incident, args=(chosen,))


{"Dashboard": dashboard_page, "Security Incidents": incidents_page, "Audit History": audit_page}[page]()
