"""GuardBee Security Analytics Console - synthetic suspicious-login investigation only.

Three native-Streamlit pages (Dashboard, Security Incidents, Audit History) share
one visual system. Risk facts come from engine.py, policies from retrieval.py,
AI text from ai_client.py, and decision gates from workflow.py; this module only
presents them. Data text is shown in plain-text widgets (tables, metrics) or is
Markdown-escaped first. The only HTML injected is the static stylesheet below.
"""

from __future__ import annotations

import inspect
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
st.set_page_config(
    page_title="GuardBee | Security Analytics Console",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

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
# Card tints (see the tone-* rules in STYLES); they follow engine output, never invent it.
CLASSIFICATION_TONES = {"SUSPICIOUS": "red", "NORMAL": "green", "INSUFFICIENT_EVIDENCE": "amber"}
SEVERITY_TONES = {"HIGH": "red", "MEDIUM": "amber", "LOW": "blue"}
# Keyed containers (needed for per-card tints) arrived in newer Streamlit; older ones stay untinted.
CONTAINER_TAKES_KEY = "key" in inspect.signature(st.container).parameters
DECISION_LABELS = {"APPROVED": "✅ APPROVED", "REJECTED": "⛔ REJECTED"}
NOT_ASSIGNED = "Not assigned"
NOT_CLASSIFIED = "Not classified"
RISK_NOTE = (
    "The risk score (0–100) is a deterministic rule-based estimate, not a probability. "
    "A high score is not proof of compromise."
)
UNKNOWNS = (
    "Whether the account owner made these logins; the data does not verify identity.",
    "Device, browser, and VPN details; they are not present in the data.",
    "Any activity outside this synthetic event set.",
)
STEP_MARKS = {"done": ":green[✔]", "active": ":violet[●]", "locked": ":gray[○]", "blocked": ":red[✖]"}

# Static stylesheet: no data is ever interpolated into it.
STYLES = """
<style>
:root {
  --gb-sidebar: #0B1220; --gb-sidebar-panel: #172337; --gb-bg: #F4F7FC; --gb-card: #FFFFFF;
  --gb-text: #14213D; --gb-muted: #64748B; --gb-accent: #4F46E5; --gb-accent-2: #38BDF8;
  --gb-red: #EF4444; --gb-green: #22C55E; --gb-amber: #F59E0B; --gb-border: #E2E8F0;
}
html, body, .stApp { font-family: Inter, "Segoe UI", system-ui, -apple-system, Roboto, sans-serif; }
.stApp { background: var(--gb-bg); }
[data-testid="stMainBlockContainer"] { padding-top: 2rem; padding-bottom: 3rem; max-width: 1360px; }
h1, h2, h3, h4 { color: var(--gb-text); letter-spacing: -0.01em; }
h1 { font-weight: 750 !important; }

/* Sidebar */
[data-testid="stSidebar"] {
  background: linear-gradient(180deg, #0B1220 0%, #0F1730 45%, #1A1E4A 80%, #2B2675 100%);
  border-right: 1px solid #1E293B; }
@media (min-width: 992px) { [data-testid="stSidebar"] { min-width: 248px !important; max-width: 248px !important; } }
[data-testid="stSidebar"] p, [data-testid="stSidebar"] li, [data-testid="stSidebar"] label,
[data-testid="stSidebar"] span, [data-testid="stSidebar"] small { color: #CBD5E1; }
[data-testid="stSidebar"] strong { color: #FFFFFF; }
[data-testid="stSidebarNavLink"] { border-radius: 8px; margin: 2px 0; padding: 0.45rem 0.75rem; }
[data-testid="stSidebarNavLink"]:hover { background: var(--gb-sidebar-panel); }
[data-testid="stSidebarNavLink"] span { color: #CBD5E1; font-weight: 500; }
[data-testid="stSidebarNavLink"][aria-current="page"] {
  background: linear-gradient(90deg, #4F46E5 0%, #6366F1 60%, #7C3AED 100%);
  box-shadow: 0 6px 16px rgba(79, 70, 229, 0.35); }
[data-testid="stSidebarNavLink"][aria-current="page"] span { color: #FFFFFF; font-weight: 650; }
[data-testid="stSidebar"] [data-testid="stVerticalBlockBorderWrapper"],
[data-testid="stSidebar"] .gb-sidebar-card { background: var(--gb-sidebar-panel); border-color: #26344D !important; }
[data-testid="stSidebar"] hr { border-color: #1E293B; }
[data-testid="stSidebar"] .st-key-sidebar-demo {
  background: linear-gradient(135deg, #3730A3 0%, #4F46E5 55%, #6D28D9 100%) !important;
  border: none !important; border-radius: 12px; box-shadow: 0 8px 20px rgba(49, 46, 129, 0.45); }
[data-testid="stSidebar"] .st-key-sidebar-demo p, [data-testid="stSidebar"] .st-key-sidebar-demo span { color: #E0E7FF; }

/* Cards */
[data-testid="stMain"] [data-testid="stVerticalBlockBorderWrapper"] {
  background: var(--gb-card); border: 1px solid var(--gb-border) !important; border-radius: 12px;
  box-shadow: 0 1px 2px rgba(20, 33, 61, 0.04), 0 4px 16px rgba(20, 33, 61, 0.04);
}
[class*="st-key-tone-"] { border-radius: 12px; }
[class*="st-key-tone-red"] { background: linear-gradient(135deg, #FFE4E6 0%, #FFF5F6 45%, #FFFFFF 100%) !important; border-color: #FECDD3 !important; }
[class*="st-key-tone-red"] [data-testid="stMetricValue"] { color: #DC2626; }
[class*="st-key-tone-green"] { background: linear-gradient(135deg, #DCFCE7 0%, #F3FDF6 45%, #FFFFFF 100%) !important; border-color: #BBF7D0 !important; }
[class*="st-key-tone-green"] [data-testid="stMetricValue"] { color: #16A34A; }
[class*="st-key-tone-amber"] { background: linear-gradient(135deg, #FEF3C7 0%, #FFFBEB 45%, #FFFFFF 100%) !important; border-color: #FDE68A !important; }
[class*="st-key-tone-amber"] [data-testid="stMetricValue"] { color: #D97706; }
[class*="st-key-tone-blue"] { background: linear-gradient(135deg, #DBEAFE 0%, #F0F6FF 45%, #FFFFFF 100%) !important; border-color: #BFDBFE !important; }
[class*="st-key-tone-blue"] [data-testid="stMetricValue"] { color: #2563EB; }
[class*="st-key-tone-violet"] { background: linear-gradient(135deg, #EDE9FE 0%, #F7F5FF 45%, #FFFFFF 100%) !important; border-color: #DDD6FE !important; }
[class*="st-key-tone-violet"] [data-testid="stMetricValue"] { color: #6D28D9; }
[data-testid="stMain"] button[data-testid="stBaseButton-primary"]:not(:disabled) {
  background: linear-gradient(90deg, #4F46E5 0%, #6366F1 55%, #7C3AED 100%); border: none; color: #FFFFFF;
  box-shadow: 0 4px 14px rgba(79, 70, 229, 0.30); }
[data-testid="stMain"] .st-key-btn_approve button:not(:disabled) {
  background: linear-gradient(90deg, #16A34A 0%, #22C55E 100%); border: none; color: #FFFFFF;
  box-shadow: 0 4px 14px rgba(34, 197, 94, 0.30); }
[data-testid="stMain"] .st-key-btn_reject button:not(:disabled) {
  background: linear-gradient(90deg, #DC2626 0%, #EF4444 100%); border: none; color: #FFFFFF;
  box-shadow: 0 4px 14px rgba(239, 68, 68, 0.30); }
[data-testid="stMain"] button:not(:disabled):hover { filter: brightness(1.06); }
[data-testid="stMetricLabel"] p { color: var(--gb-muted); font-size: 0.78rem; font-weight: 600;
  text-transform: uppercase; letter-spacing: 0.05em; }
[data-testid="stMetricValue"] { color: var(--gb-text); font-weight: 750; font-size: clamp(1.15rem, 1.6vw, 1.7rem); }
[data-testid="stMetricLabel"] div, [data-testid="stMetricLabel"] p {
  white-space: normal !important; word-break: keep-all; overflow-wrap: normal; line-height: 1.3; }

/* Tabs, expanders, tables, buttons */
[data-testid="stTabs"] button[role="tab"] p { font-weight: 600; font-size: 0.95rem; }
[data-testid="stTabs"] [data-testid="stMarkdownContainer"] h1,
[data-testid="stTabs"] [data-testid="stMarkdownContainer"] h2 { font-size: 1.2rem; padding-top: 0.6rem; }
[data-testid="stTabs"] [data-testid="stMarkdownContainer"] h3 { font-size: 1.05rem; padding-top: 0.4rem; }
[data-testid="stExpander"] details { background: var(--gb-card); border-radius: 10px; border-color: var(--gb-border); }
[data-testid="stDataFrame"] { border-radius: 10px; }
[data-testid="stMain"] [data-testid="stElementContainer"]:has(> [data-testid="stButton"]),
[data-testid="stMain"] [data-testid="stButton"] { width: 100% !important; }
[data-testid="stMain"] button[data-testid^="stBaseButton-primary"],
[data-testid="stMain"] button[data-testid^="stBaseButton-secondary"] { border-radius: 8px; font-weight: 600; width: 100%; }
[data-testid="stCaptionContainer"] { color: var(--gb-muted); }
</style>
"""

_MARKDOWN_SPECIAL = re.compile(r"([\\`*_{}\[\]()#+\-.!|<>~$:@])")


def md(value: Any) -> str:
    """Escape Markdown so data text is always shown literally."""
    return _MARKDOWN_SPECIAL.sub(r"\\\1", str(value))


def code(value: Any) -> str:
    """Show an identifier (account, IP, ID) literally as inline code; never a link."""
    return "`" + str(value).replace("`", "'") + "`"


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


def sync_incident_picker() -> None:
    st.session_state.current_incident_id = st.session_state.incident_picker


def go_to_incident(incident_id: str) -> None:
    """Open one incident on the Security Incidents page with its filters cleared."""
    st.session_state.current_incident_id = incident_id
    st.session_state.incident_search = ""
    st.session_state.incident_filter = "All"
    st.switch_page(INCIDENTS_PAGE)


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
        with st.spinner("Generating AI report via Nebius Token Factory. GuardBee never fabricates reports..."):
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
    return value.replace("_", " ") if value else NOT_CLASSIFIED


def classification_badge(analysis: dict[str, Any]) -> str:
    value = classification_of(analysis)
    if not value:
        return f":gray-background[{NOT_CLASSIFIED.upper()}]"
    return f":{CLASSIFICATIONS[value][0]}-background[{value.replace('_', ' ')}]"


def severity_text(analysis: dict[str, Any]) -> str:
    return analysis.get("severity") or NOT_ASSIGNED


def severity_badge(analysis: dict[str, Any]) -> str:
    severity = analysis.get("severity")
    if severity in SEVERITY_COLORS:
        return f":{SEVERITY_COLORS[severity]}-background[{severity}]"
    return f":gray-background[{md(severity_text(analysis))}]"


def priority_text(analysis: dict[str, Any]) -> str:
    return analysis.get("investigation_priority") or "Not provided"


def short_text(value: str) -> str:
    """Compact form for cards and tables; captions explain what a dash means."""
    return "—" if value in (NOT_CLASSIFIED, "Not provided") else value


def event_time(event: dict[str, Any]) -> datetime:
    return datetime.fromisoformat(event["time_utc"].replace("Z", "+00:00"))


def latest_event_time(incident: dict[str, Any]) -> str:
    return max(incident["events"], key=event_time)["time_utc"]


# ---------------------------------------------------------------------------
# Reusable components
# ---------------------------------------------------------------------------
def page_header(title: str, subtitle: str, description: str) -> None:
    st.title(title)
    st.markdown(f"**{subtitle}**")
    st.caption(description)


def demo_banner() -> None:
    st.warning(
        "**Demo only — simulated environment.** Synthetic login incidents from a static JSON file. "
        "Not live monitoring; GuardBee never blocks accounts, revokes sessions, or changes any system.",
        icon="⚠️",
    )


def card(parent: Any = st, key: str | None = None) -> Any:
    """Bordered card; a key adds an st-key-* class that the stylesheet can tint."""
    if key and CONTAINER_TAKES_KEY:
        return parent.container(border=True, key=key)
    return parent.container(border=True)


def metric_card(
    column: Any, label: str, value: Any, caption: str, help_text: str | None = None, tone: str | None = None
) -> None:
    key = f"tone-{tone}-{re.sub(r'[^a-z0-9]+', '-', label.lower())}" if tone else None
    with card(column, key):
        st.metric(label, value, help=help_text)
        st.caption(caption)


def incident_table(incident_list: list[dict[str, Any]], show_latest: bool = True) -> None:
    st.dataframe(
        [
            {
                "Incident": incident["id"],
                "Title": incident["title"],
                "Classification": short_text(classification_text(analyses[incident["id"]])),
                "Risk score": analyses[incident["id"]]["risk_score"],
                "Severity": severity_text(analyses[incident["id"]]),
                "Priority": short_text(priority_text(analyses[incident["id"]])),
                **({"Latest event (UTC)": latest_event_time(incident)} if show_latest else {}),
            }
            for incident in incident_list
        ],
        hide_index=True,
        column_config={
            "Incident": st.column_config.TextColumn("Incident", width="small"),
            "Title": st.column_config.TextColumn("Title", width="medium"),
            "Classification": st.column_config.TextColumn("Classification", width="small"),
            "Risk score": st.column_config.ProgressColumn(
                "Risk score", min_value=0, max_value=100, format="%d", help=RISK_NOTE, width="small"
            ),
            "Severity": st.column_config.TextColumn("Severity", width="small"),
            "Priority": st.column_config.TextColumn("Priority", width="small"),
            "Latest event (UTC)": st.column_config.TextColumn("Latest event (UTC)", width="medium"),
        },
    )


def empty_state(message: str, icon: str = "ℹ️") -> None:
    with st.container(border=True):
        st.info(message, icon=icon)


def render_stepper(slot: Any, steps: list[tuple[str, str, str]]) -> None:
    with slot:
        for column, (index, (title, state, detail)) in zip(st.columns(len(steps)), enumerate(steps, 1)):
            column.markdown(f"{STEP_MARKS[state]} **{index} · {title}**")
            column.caption(detail)


def render_sidebar() -> None:
    with st.sidebar:
        st.divider()
        with card(st, "sidebar-demo"):
            st.markdown("**⚠️ Demo only**")
            st.caption(
                "Synthetic incidents and simulated decisions. No live monitoring and no real account actions."
            )
        st.markdown("**AI provider**")
        if read_api_key():
            st.caption("🟢 Nebius API key configured")
        else:
            st.caption("🟠 No Nebius API key — AI reports will show an error")
        st.caption(f"Model: {md(read_model())}")
        st.caption(f"Simulated decisions this session: {len(st.session_state.audit)}")


# ---------------------------------------------------------------------------
# Data
# ---------------------------------------------------------------------------
initialize_session()
st.html(STYLES)
logo = ROOT / "assets" / "guardbee_logo.svg"
if logo.exists():
    st.logo(str(logo), size="large")

try:
    with st.spinner("Loading synthetic incidents..."):
        incidents = load_incidents(ROOT / "data" / "incidents.json")
        policies = load_policies(ROOT / "data" / "policies.json")
except DataValidationError as exc:
    st.title("GuardBee")
    st.markdown("**Security Analytics Console**")
    st.error(
        "GuardBee could not load its synthetic data safely, so no incidents, counts, or audit links are shown.",
        icon="🚫",
    )
    st.caption(f"Validation error: {md(exc)} Fix the data file and reload the app.")
    st.stop()

incident_by_id = {incident["id"]: incident for incident in incidents}
analyses = {incident["id"]: analyze_incident(incident) for incident in incidents}
any_classified = any(classification_of(analysis) for analysis in analyses.values())
if st.session_state.current_incident_id not in incident_by_id:
    st.session_state.current_incident_id = incidents[0]["id"]


# ---------------------------------------------------------------------------
# Page 1 - Dashboard
# ---------------------------------------------------------------------------
def dashboard_page() -> None:
    page_header(
        "GuardBee",
        "Security Analytics Console",
        "Overview of the synthetic login incidents in data/incidents.json, analysed by GuardBee's deterministic "
        "rules engine. Open an incident to investigate its evidence, policies, and AI report.",
    )
    demo_banner()

    cards = st.columns(5)
    metric_card(cards[0], "Valid incidents", len(incidents), "Loaded and validated", tone="blue")
    if any_classified:
        for column, key, caption in zip(
            cards[1:4],
            ("SUSPICIOUS", "NORMAL", "INSUFFICIENT_EVIDENCE"),
            ("Match a suspicious pattern", "No suspicious pattern found", "Cannot classify either way"),
        ):
            count = sum(1 for analysis in analyses.values() if classification_of(analysis) == key)
            metric_card(column, key.replace("_", " ").title(), count, caption, tone=CLASSIFICATION_TONES[key])
    else:
        for column, label, tone in zip(
            cards[1:4], ("Suspicious", "Normal", "Insufficient evidence"), ("red", "green", "amber")
        ):
            metric_card(column, label, "—", "Engine does not classify yet", tone=tone)
    metric_card(
        cards[4], "Validation", "Passed", "Fail-closed loader: 0 rejected",
        help_text="Every record must pass validation or loading stops. Partial processing is not implemented yet.",
        tone="violet",
    )

    left, right = st.columns([1, 2], gap="medium")
    with left:
        with st.container(border=True):
            st.subheader("Classification overview")
            if any_classified:
                for key, (color, wording) in CLASSIFICATIONS.items():
                    count = sum(1 for analysis in analyses.values() if classification_of(analysis) == key)
                    st.markdown(f":{color}-background[{key.replace('_', ' ')}] **{count}**")
                    st.progress(count / len(incidents))
                    st.caption(wording)
            else:
                st.info(
                    "Classification counts are unavailable: engine.py does not return a classification yet. "
                    "GuardBee does not infer one from the risk score.",
                    icon="ℹ️",
                )
            st.markdown("**Severity distribution**")
            for label in ("HIGH", "MEDIUM", "LOW", None):
                count = sum(1 for analysis in analyses.values() if analysis.get("severity") == label)
                if label is None and not count:
                    continue
                name = label.title() if label else NOT_ASSIGNED
                st.progress(count / len(incidents), text=f"{name}: {count} of {len(incidents)}")
            st.caption(RISK_NOTE)

    with right:
        with st.container(border=True):
            st.subheader("Recent incidents")
            st.caption("Newest activity first (by latest event time). Values come directly from the engine analysis.")
            recent = sorted(incidents, key=lambda incident: latest_event_time(incident), reverse=True)
            incident_table(recent, show_latest=False)
            if not any_classified:
                st.caption("— means the engine does not provide this field yet.")
            pick, action = st.columns([3, 2], vertical_alignment="bottom")
            chosen = pick.selectbox(
                "Select an incident",
                [incident["id"] for incident in recent],
                format_func=lambda identifier: f"{identifier} · {incident_by_id[identifier]['title']}",
                key="dashboard_pick",
            )
            if action.button("Open investigation →", key="dashboard_open", type="primary"):
                go_to_incident(chosen)


# ---------------------------------------------------------------------------
# Page 2 - Security Incidents
# ---------------------------------------------------------------------------
def render_incident_list() -> str | None:
    with st.container(border=True):
        st.markdown("**Incidents**")
        search = st.text_input(
            "Search", placeholder="ID, title, account, department", key="incident_search",
            label_visibility="collapsed",
        )
        filters = {"All": None, "High severity": "HIGH", "Medium severity": "MEDIUM", "Low severity": "LOW"}
        if any_classified:
            filters.update({key.replace("_", " ").title(): key for key in CLASSIFICATIONS})
        wanted = filters[st.selectbox("Filter", list(filters), key="incident_filter")]
        query = search.strip().lower()
        shown = [
            incident
            for incident in incidents
            if (
                wanted is None
                or analyses[incident["id"]].get("severity") == wanted
                or classification_of(analyses[incident["id"]]) == wanted
            )
            and (
                not query
                or any(query in str(incident[field]).lower() for field in ("id", "title", "account", "department"))
            )
        ]
        if not shown:
            st.info("No incidents match the search or filter.")
            return None
        shown_ids = [incident["id"] for incident in shown]
        if st.session_state.current_incident_id not in shown_ids:
            st.session_state.current_incident_id = shown_ids[0]
        st.session_state.incident_picker = st.session_state.current_incident_id
        selected = st.radio(
            "Select incident",
            shown_ids,
            format_func=lambda identifier: (
                f"{identifier} ({analyses[identifier]['risk_score']}/100) — {incident_by_id[identifier]['title']}"
            ),
            key="incident_picker",
            on_change=sync_incident_picker,
            label_visibility="collapsed",
        )
        st.caption(f"Showing {len(shown)} of {len(incidents)} incidents")

    analysis = analyses[selected]
    with st.container(border=True):
        st.markdown(f"**{md(selected)}**")
        st.caption(md(incident_by_id[selected]["title"]))
        st.markdown(f"{classification_badge(analysis)} {severity_badge(analysis)}")
        st.progress(analysis["risk_score"] / 100, text=f"Risk score {analysis['risk_score']}/100")
        st.caption(f"Investigation priority: {md(priority_text(analysis))}")
    return selected


def render_timeline(incident: dict[str, Any], analysis: dict[str, Any]) -> None:
    evidence = set(analysis["evidence_ids"])
    known = set(incident.get("known_ips", []))
    st.caption("Sorted chronologically by time_utc. Highlighted rows are evidence cited by triggered rules.")
    st.dataframe(
        [
            {
                "Event": event["id"],
                "Time (UTC)": event["time_utc"],
                "Type": "Failed login" if event["type"] == "login_failed" else "Successful login",
                "IP": event["ip"],
                "IP status": "Known" if event["ip"] in known else "Unfamiliar",
                "Country": event.get("country", ""),
                "Rule evidence": event["id"] in evidence,
            }
            for event in sorted(incident["events"], key=event_time)
        ],
        hide_index=True,
    )


def render_rules(incident: dict[str, Any], analysis: dict[str, Any]) -> None:
    if analysis["rule_hits"]:
        st.dataframe(
            [
                {
                    "Rule": hit["rule_id"],
                    "Finding": hit["flag"],
                    "Points": hit["points"],
                    "Evidence events": len(hit["evidence_ids"]),
                }
                for hit in analysis["rule_hits"]
            ],
            hide_index=True,
        )
        with st.expander("Evidence references by rule", expanded=True):
            for hit in analysis["rule_hits"]:
                references = " ".join(code(event_id) for event_id in hit["evidence_ids"]) or "account context only"
                st.markdown(f"{code(hit['rule_id'])} → {references}")
        total = sum(hit["points"] for hit in analysis["rule_hits"])
        st.caption(f"Rule points total {total}; the risk score is capped at 100.")
    else:
        st.info("No configured rule matched the available events.")

    events = incident["events"]
    known = set(incident.get("known_ips", []))
    failed = sum(1 for event in events if event["type"] == "login_failed")
    unfamiliar = sorted({event["ip"] for event in events if event["ip"] not in known})
    facts, inference, unknowns = st.columns(3, gap="small")
    with facts.container(border=True):
        st.markdown("**Observed facts**")
        st.markdown(
            md(
                f"{failed} failed and {len(events) - failed} successful logins "
                f"from {len({event['ip'] for event in events})} IP address(es)."
            )
        )
        st.markdown(md(f"Unfamiliar IPs: {', '.join(unfamiliar)}.") if unfamiliar else "All events came from known IPs.")
    with inference.container(border=True):
        st.markdown("**Engine interpretation**")
        for flag in analysis["flags"] or ["No configured rule matched."]:
            st.markdown(f"- {md(flag)}")
        st.caption(md(f"Suggested (simulated) action: {analysis['suggested_action']}"))
    with unknowns.container(border=True):
        st.markdown("**Unknowns & limitations**")
        for unknown in UNKNOWNS:
            st.markdown(f"- {md(unknown)}")


def render_policies(matched_policies: list[dict[str, Any]]) -> None:
    st.caption(
        f"Retrieved locally with TF-IDF cosine similarity from data/policies.json. "
        f"Only passages scoring at least {DEFAULT_MIN_SIMILARITY:.2f} are shown."
    )
    if not matched_policies:
        st.warning(
            "No policy passage met the similarity threshold. AI reports and decisions are unavailable "
            "without policy context to cite."
        )
        return
    for index, policy in enumerate(matched_policies):
        label = f"{policy['id']} · {policy['title']} · similarity {policy['match_score']:.3f}"
        with st.expander(md(label), expanded=index == 0):
            st.markdown(md(policy["text"]))


def render_ai_panel(
    incident: dict[str, Any], analysis: dict[str, Any], matched_policies: list[dict[str, Any]], context_id: str
) -> None:
    st.caption(
        f"✨ AI-generated content · NVIDIA Nemotron via Nebius Token Factory · model {md(read_model())}. "
        "Separate from the deterministic engine results."
    )
    if st.button(
        "✨ Generate AI Report",
        type="primary",
        key="ai_request_btn",
        disabled=not matched_policies,
    ):
        run_ai_analysis(incident, analysis, matched_policies, context_id)

    if st.session_state.report:
        st.success(md(st.session_state.report_status), icon="✅")
        cited_events, cited_policies = extract_citation_ids(st.session_state.report)
        titles = {policy["id"].upper(): policy["title"] for policy in matched_policies}
        st.markdown("**Validated evidence citations:** " + " ".join(f"`{event_id}`" for event_id in cited_events))
        st.markdown(
            "**Validated policy citations:** "
            + "; ".join(f"`{policy_id}` {md(titles.get(policy_id, ''))}" for policy_id in cited_policies)
        )
        with st.container(border=True):
            st.markdown(st.session_state.report)
        st.caption(
            "Citation checks prove the IDs belong to this incident and its retrieved policies, not that every "
            "sentence is correct. Treat inferred risk and unknowns as unconfirmed."
        )
    elif st.session_state.report_status:
        st.error(md(st.session_state.report_status), icon="🚫")
        st.caption(
            "No report was generated or substituted. Check the API key, network access, account credits, "
            "and configured model, then retry."
        )
        if st.button("↻ Retry AI Report", key="ai_retry_btn", disabled=not matched_policies):
            run_ai_analysis(incident, analysis, matched_policies, context_id)
            st.rerun()
    elif matched_policies:
        st.info("Generate an AI report to unlock the simulated decision. A Nebius API key is required.")


def render_decision_panel(incident: dict[str, Any], analysis: dict[str, Any], context_id: str) -> bool:
    can_decide = can_record_decision(
        st.session_state.report,
        st.session_state.report_context_id,
        context_id,
        st.session_state.active_report_id,
        st.session_state.decision,
    )
    with st.container(border=True):
        st.subheader("Analyst decision")
        st.markdown(":red-background[SIMULATED ACTION — NO REAL ACCOUNT ACTION]")
        st.markdown(f"**Proposed action:** {md(analysis['suggested_action'])}")
        decision = st.session_state.decision
        if decision:
            st.success(
                md(f"{decision['decision']} recorded at {decision['time_utc']} (UTC): {decision['outcome']}"),
                icon="📝",
            )
            st.caption("A decision is already recorded for this report. Generate a new report to decide again.")
        elif not st.session_state.report:
            st.warning("Locked until a citation-validated AI report is available for this incident.", icon="🔒")
        elif not can_decide:
            st.warning(
                "Locked: the AI report belongs to a different incident or analysis context. Generate a new report.",
                icon="🔒",
            )
        approve, reject = st.columns(2)
        for column, label, key, verdict, outcome, kind in (
            (approve, "Approve (simulated)", "btn_approve", "APPROVED",
             "Simulated session-revocation response recorded; no external system was changed.", "primary"),
            (reject, "Reject (simulated)", "btn_reject", "REJECTED",
             "No action taken; recommendation rejected by demo analyst.", "secondary"),
        ):
            if column.button(label, key=key, type=kind, disabled=not can_decide):
                if audit_decision(incident, verdict, outcome, context_id):
                    st.rerun()
                st.error("The decision was not recorded: the report is no longer valid for this context.")
        if decision and st.button("View in Audit History →", key="open_audit"):
            st.switch_page(AUDIT_PAGE)
    return can_decide


def render_investigation(incident: dict[str, Any]) -> None:
    reset_investigation_state(incident["id"])
    analysis = analyses[incident["id"]]
    query = " ".join(
        [incident["title"], incident["department"], *analysis["flags"], analysis["suggested_action"]]
    )
    matched_policies = retrieve_policies(query, policies)
    context_id = analysis_context_id(incident, analysis, matched_policies)

    with st.container(border=True):
        st.subheader(md(incident["title"]))
        known_ips = ", ".join(incident.get("known_ips", [])) or "none listed"
        st.caption(
            f"{code(incident['id'])}  ·  Account {code(incident['account'])}  ·  "
            f"Department {md(incident['department'])}  ·  Known IPs {code(known_ips)}"
        )
        classification = classification_of(analysis)
        if classification:
            st.markdown(f"{classification_badge(analysis)} {CLASSIFICATIONS[classification][1]}")
        else:
            st.markdown(
                f"{classification_badge(analysis)} engine.py does not provide a classification yet. "
                "A low or zero score alone does not show that this activity is normal."
            )

    cards = st.columns(4)
    metric_card(
        cards[0], "Classification", short_text(classification_text(analysis)),
        "From engine.py" if classification_of(analysis) else "Not classified by the engine yet",
        help_text=classification_text(analysis),
        tone=CLASSIFICATION_TONES.get(classification_of(analysis) or "", "violet"),
    )
    severity_tone = SEVERITY_TONES.get(analysis.get("severity") or "", "violet")
    metric_card(
        cards[1], "Risk score", f"{analysis['risk_score']} / 100", "Rule-based, not a probability", RISK_NOTE,
        tone=severity_tone,
    )
    metric_card(cards[2], "Severity", severity_text(analysis), "Derived by engine.py", tone=severity_tone)
    metric_card(
        cards[3], "Investigation priority", short_text(priority_text(analysis)),
        "Backend-provided" if analysis.get("investigation_priority") else "Not provided by the backend yet",
        help_text=priority_text(analysis),
        tone="violet",
    )

    stepper = st.container(border=True)

    timeline_tab, rules_tab, policy_tab, ai_tab = st.tabs(
        ["🕒 Timeline", "📐 Rules & Evidence", "📚 Relevant Policies", "✨ AI Analysis"]
    )
    with timeline_tab:
        render_timeline(incident, analysis)
    with rules_tab:
        render_rules(incident, analysis)
    with policy_tab:
        render_policies(matched_policies)
    with ai_tab:
        render_ai_panel(incident, analysis, matched_policies, context_id)

    can_decide = render_decision_panel(incident, analysis, context_id)

    if st.session_state.report:
        ai_step = ("AI report", "done", "Citations validated")
    elif st.session_state.report_status:
        ai_step = ("AI report", "blocked", "Not usable")
    elif matched_policies:
        ai_step = ("AI report", "active", "Ready to generate")
    else:
        ai_step = ("AI report", "locked", "Needs policy context")
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
    page_header(
        "Security Incidents",
        "Investigation workspace",
        "Select an incident to review its timeline, triggered rules, relevant policies, and AI report, "
        "then record one simulated decision.",
    )
    left, main = st.columns([1.25, 3], gap="medium")
    with left:
        selected = render_incident_list()
    with main:
        if selected:
            render_investigation(incident_by_id[selected])
        else:
            empty_state("Adjust the search or filter to select an incident.")


# ---------------------------------------------------------------------------
# Page 3 - Audit History
# ---------------------------------------------------------------------------
def audit_page() -> None:
    page_header(
        "Audit History",
        "Simulated analyst decisions",
        "Every Approve or Reject decision recorded against a citation-validated AI report, newest first.",
    )
    st.markdown(":red-background[SIMULATION ONLY — NO REAL ACCOUNT ACTIONS WERE TAKEN]")
    st.warning(
        "Session-only storage: the persistent SQLite audit store is not implemented yet, so these records "
        "disappear when the browser session ends or the app restarts.",
        icon="⚠️",
    )
    records = list(reversed(st.session_state.audit))
    if not records:
        empty_state(
            "No simulated decisions have been recorded in this session yet. Open Security Incidents, "
            "generate an AI report, and approve or reject it.",
            icon="📭",
        )
        return

    with st.container(border=True):
        filters = st.columns(2)
        decision_filter = filters[0].selectbox("Decision", ["All", "APPROVED", "REJECTED"], key="audit_decision")
        incident_filter = filters[1].selectbox(
            "Incident", ["All", *dict.fromkeys(record["incident_id"] for record in records)], key="audit_incident"
        )
        shown = [
            record
            for record in records
            if decision_filter in ("All", record["decision"]) and incident_filter in ("All", record["incident_id"])
        ]
        st.dataframe(
            [
                {
                    "Time (UTC)": record["time_utc"],
                    "Incident": record["incident_id"],
                    "Decision": DECISION_LABELS.get(record["decision"], record["decision"]),
                    "Simulation only": record["simulation_only"],
                    "Actor": record["actor"],
                    "Report reference": record["report_id"],
                }
                for record in shown
            ],
            hide_index=True,
        )
        st.caption(f"Showing {len(shown)} of {len(records)} record(s).")

    if shown:
        with st.container(border=True):
            st.subheader("Record detail")
            index = st.selectbox(
                "Record",
                range(len(shown)),
                format_func=lambda i: f"{shown[i]['time_utc']} · {shown[i]['incident_id']} · {shown[i]['decision']}",
                key="audit_record",
            )
            record = shown[index]
            details = st.columns(3)
            details[0].markdown(f"**Decision**  \n{DECISION_LABELS.get(record['decision'], md(record['decision']))}")
            details[1].markdown(f"**Incident**  \n{md(record['incident_id'])}")
            details[2].markdown(f"**Time (UTC)**  \n{md(record['time_utc'])}")
            st.markdown(f"**Outcome:** {md(record['outcome'])}")
            st.caption(md(f"Report reference: {record['report_id']}"))
            if record["incident_id"] in incident_by_id and st.button("Open incident →", key="audit_open"):
                go_to_incident(record["incident_id"])


DASHBOARD_PAGE = st.Page(dashboard_page, title="Dashboard", icon=":material/dashboard:", default=True)
INCIDENTS_PAGE = st.Page(incidents_page, title="Security Incidents", icon=":material/shield:", url_path="incidents")
AUDIT_PAGE = st.Page(audit_page, title="Audit History", icon=":material/history:", url_path="audit")

navigation = st.navigation([DASHBOARD_PAGE, INCIDENTS_PAGE, AUDIT_PAGE], position="sidebar")
render_sidebar()
navigation.run()
