"""GuardBee Streamlit MVP – synthetic suspicious-login investigation only.

Four-view Wazuh-inspired security dashboard:
  View 1 – Dashboard      (Security Overview / at-a-glance metrics)
  View 2 – Incidents      (Browse & filter the synthetic incident collection)
  View 3 – Incident Detail (Investigate one incident, AI explanation, Approve/Reject)
  View 4 – Audit History  (Simulated session-only decision audit log)

Backend contracts (engine.py, retrieval.py, ai_client.py, data_loader.py,
workflow.py) are NOT modified.  All UI state is managed in st.session_state.
"""

from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import streamlit as st

from ai_client import AIReportError, configured_model, generate_report, validate_report_citations
from data_loader import DataValidationError, load_incidents, load_policies
from engine import analyze_incident
from retrieval import DEFAULT_MIN_SIMILARITY, retrieve_policies
from workflow import analysis_context_id, build_decision_record, can_record_decision

ROOT = Path(__file__).parent

st.set_page_config(
    page_title="GuardBee | Security Decision Copilot",
    page_icon=str(ROOT / "assets" / "favicon.png"),
    layout="wide",
)

# ---------------------------------------------------------------------------
# Global CSS — Wazuh-inspired dark SOC/SIEM theme
# ---------------------------------------------------------------------------
st.markdown(
    """
<style>
/* ── Fonts ──────────────────────────────────────────────────────────── */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');

html, body, [class*="css"], .stApp {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    background-color: #0a1628 !important;
    color: #e2e8f0;
}

/* ── Main container ──────────────────────────────────────────────────── */
.main .block-container {
    padding-top: 1rem;
    padding-bottom: 2rem;
    max-width: 1300px;
}

/* ── Sidebar ──────────────────────────────────────────────────────────── */
section[data-testid="stSidebar"] {
    background: #06101f !important;
    border-right: 1px solid #1e3a5f;
    min-width: 230px !important;
    max-width: 260px !important;
}
section[data-testid="stSidebar"] .block-container {
    padding-top: 1.2rem;
    padding-left: 1rem;
    padding-right: 1rem;
}
.gb-sidebar-brand {
    font-size: 1.15rem;
    font-weight: 700;
    color: #e2e8f0;
    display: flex;
    align-items: center;
    gap: 0.5rem;
    padding-bottom: 1rem;
    border-bottom: 1px solid #1e3a5f;
    margin-bottom: 1rem;
    letter-spacing: -0.01em;
}
.gb-brand-badge {
    width: 28px; height: 28px;
    background: #3b82f6;
    border-radius: 6px;
    display: flex; align-items: center; justify-content: center;
    font-size: 0.9rem;
}
.gb-sidebar-section {
    font-size: 0.65rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.12em;
    color: #4a7fa5;
    margin: 1rem 0 0.4rem;
}
.gb-nav-item {
    display: flex;
    align-items: center;
    gap: 0.55rem;
    padding: 0.55rem 0.75rem;
    border-radius: 6px;
    font-size: 0.85rem;
    font-weight: 500;
    color: #94a3b8;
    cursor: pointer;
    margin-bottom: 0.15rem;
    transition: background 0.15s;
    border: none;
    background: transparent;
    text-decoration: none;
    user-select: none;
}
.gb-nav-item:hover { background: #111a2e; color: #e2e8f0; }
.gb-nav-item.active { background: #1e3a5f; color: #60a5fa; font-weight: 600; }
.gb-nav-dot { width: 7px; height: 7px; border-radius: 50%; flex-shrink: 0; }
.gb-sidebar-footer {
    font-size: 0.72rem;
    color: #4a7fa5;
    line-height: 1.55;
    margin-top: 1.5rem;
    padding-top: 1rem;
    border-top: 1px solid #1e3a5f;
}

/* ── Page header bar ─────────────────────────────────────────────────── */
.gb-topbar {
    background: #111a2e;
    border: 1px solid #1e3a5f;
    border-radius: 8px;
    padding: 0.9rem 1.4rem;
    margin-bottom: 1.2rem;
    display: flex;
    align-items: center;
    justify-content: space-between;
}
.gb-topbar-left { display: flex; flex-direction: column; }
.gb-topbar-title {
    font-size: 1.2rem;
    font-weight: 700;
    color: #e2e8f0;
    letter-spacing: -0.01em;
    margin: 0;
}
.gb-topbar-sub {
    font-size: 0.78rem;
    color: #64748b;
    margin-top: 0.15rem;
}
.gb-topbar-badge {
    background: #0f2940;
    border: 1px solid #1e3a5f;
    border-radius: 6px;
    padding: 0.35rem 0.85rem;
    font-size: 0.75rem;
    color: #60a5fa;
    font-weight: 600;
    font-family: 'JetBrains Mono', monospace;
}
.gb-safety-bar {
    background: #0f2940;
    border: 1px solid #1e3a5f;
    border-left: 3px solid #3b82f6;
    border-radius: 6px;
    padding: 0.6rem 1rem;
    font-size: 0.79rem;
    color: #94a3b8;
    margin-bottom: 1.2rem;
    display: flex;
    align-items: center;
    gap: 0.55rem;
}

/* ── Metric cards ────────────────────────────────────────────────────── */
.gb-metrics-row { display: flex; gap: 0.85rem; margin-bottom: 1.2rem; flex-wrap: wrap; }
.gb-metric {
    background: #111a2e;
    border: 1px solid #1e3a5f;
    border-radius: 8px;
    padding: 1.1rem 1.3rem;
    flex: 1;
    min-width: 140px;
    position: relative;
    overflow: hidden;
}
.gb-metric::before {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 3px;
    background: var(--accent, #3b82f6);
    border-radius: 8px 8px 0 0;
}
.gb-metric-label {
    font-size: 0.7rem;
    color: #64748b;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    font-weight: 600;
    margin-bottom: 0.5rem;
}
.gb-metric-value {
    font-size: 2rem;
    font-weight: 700;
    color: #e2e8f0;
    line-height: 1;
    font-family: 'JetBrains Mono', monospace;
}
.gb-metric-sub {
    font-size: 0.72rem;
    color: #64748b;
    margin-top: 0.3rem;
}

/* ── Section headers ─────────────────────────────────────────────────── */
.gb-section-header {
    font-size: 0.72rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    color: #4a7fa5;
    padding: 0.4rem 0 0.4rem;
    border-bottom: 1px solid #1e3a5f;
    margin-bottom: 0.9rem;
    display: flex;
    align-items: center;
    gap: 0.4rem;
}

/* ── Severity / classification badges ───────────────────────────────── */
.sev-badge {
    display: inline-flex;
    align-items: center;
    gap: 0.35rem;
    padding: 0.2rem 0.65rem;
    border-radius: 5px;
    font-weight: 600;
    font-size: 0.72rem;
    letter-spacing: 0.05em;
    text-transform: uppercase;
    white-space: nowrap;
}
.sev-high    { background: #3b0f1a; color: #f87171; border: 1px solid #7f1d2e; }
.sev-medium  { background: #2d1f00; color: #fbbf24; border: 1px solid #78450c; }
.sev-low     { background: #052010; color: #4ade80; border: 1px solid #134d28; }
.sev-info    { background: #0f1e3a; color: #60a5fa; border: 1px solid #1e3a5f; }

/* ── Data table wrapper ──────────────────────────────────────────────── */
.gb-table-wrap {
    background: #111a2e;
    border: 1px solid #1e3a5f;
    border-radius: 8px;
    overflow: hidden;
    margin-bottom: 1rem;
}
.gb-table-head {
    display: grid;
    padding: 0.6rem 1rem;
    background: #0f2940;
    font-size: 0.68rem;
    font-weight: 700;
    color: #4a7fa5;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    gap: 0.5rem;
}
.gb-table-row {
    display: grid;
    padding: 0.7rem 1rem;
    font-size: 0.82rem;
    color: #cbd5e1;
    gap: 0.5rem;
    border-top: 1px solid #1a2d47;
    align-items: center;
    cursor: pointer;
    transition: background 0.12s;
}
.gb-table-row:hover { background: #142236; }

/* ── Incident table: 7 columns ──────────────────────────────────────── */
.gb-inc-cols {
    grid-template-columns: 90px 1fr 150px 110px 80px 100px 130px;
}

/* ── Timeline table: 5 columns ──────────────────────────────────────── */
.gb-timeline-cols {
    grid-template-columns: 80px 170px 140px 140px 100px;
}

/* ── Monospace cells ─────────────────────────────────────────────────── */
.mono {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.78rem;
    color: #7dd3fc;
}

/* ── Info / detail cards ─────────────────────────────────────────────── */
.gb-info-card {
    background: #111a2e;
    border: 1px solid #1e3a5f;
    border-radius: 8px;
    padding: 1rem 1.25rem;
    margin-bottom: 0.9rem;
    font-size: 0.86rem;
}
.gb-info-card .field-label {
    font-size: 0.67rem;
    color: #4a7fa5;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    font-weight: 600;
    margin-bottom: 0.2rem;
}
.gb-info-card .field-value { color: #e2e8f0; font-weight: 500; }
.gb-info-fields { display: flex; gap: 2rem; flex-wrap: wrap; }

/* ── Rule-hit cards ──────────────────────────────────────────────────── */
.gb-rule-card {
    background: #111a2e;
    border: 1px solid #1e3a5f;
    border-left: 3px solid #3b82f6;
    border-radius: 0 8px 8px 0;
    padding: 0.8rem 1.1rem;
    margin-bottom: 0.7rem;
}
.gb-rule-id { font-family: 'JetBrains Mono', monospace; font-size: 0.7rem; color: #3b82f6; font-weight: 600; margin-bottom: 0.15rem; }
.gb-rule-flag { font-size: 0.88rem; color: #e2e8f0; font-weight: 600; margin-bottom: 0.3rem; }
.gb-rule-pts { font-size: 0.74rem; color: #64748b; }
.gb-rule-evids { margin-top: 0.4rem; display: flex; flex-wrap: wrap; gap: 0.35rem; }
.gb-evid-tag {
    background: #0f2940; color: #60a5fa;
    font-family: 'JetBrains Mono', monospace; font-size: 0.7rem;
    padding: 0.12rem 0.45rem; border-radius: 4px; border: 1px solid #1e3a5f;
}
.gb-no-rules {
    background: #052010; border: 1px solid #134d28; border-radius: 6px;
    padding: 0.8rem 1.1rem; color: #4ade80; font-size: 0.85rem;
    display: flex; align-items: center; gap: 0.45rem;
}

/* ── Policy cards ────────────────────────────────────────────────────── */
.gb-policy-card {
    background: #111a2e;
    border: 1px solid #1e3a5f;
    border-left: 3px solid #0ea5e9;
    border-radius: 0 8px 8px 0;
    padding: 0.9rem 1.15rem;
    margin-bottom: 0.75rem;
}
.gb-policy-id { font-family: 'JetBrains Mono', monospace; font-size: 0.7rem; color: #0ea5e9; font-weight: 600; margin-bottom: 0.15rem; }
.gb-policy-title { font-size: 0.9rem; color: #e2e8f0; font-weight: 600; margin-bottom: 0.5rem; }
.gb-policy-sim-row { display: flex; align-items: center; gap: 0.6rem; margin-bottom: 0.55rem; }
.gb-policy-sim-label { font-size: 0.7rem; color: #64748b; white-space: nowrap; }
.gb-policy-sim-bar { flex: 1; height: 5px; background: #1e3a5f; border-radius: 3px; overflow: hidden; }
.gb-policy-sim-fill { height: 100%; background: #0ea5e9; border-radius: 3px; }
.gb-policy-sim-pct { font-size: 0.72rem; color: #0ea5e9; font-weight: 600; font-family: 'JetBrains Mono', monospace; min-width: 38px; text-align: right; }
.gb-policy-text { font-size: 0.83rem; color: #94a3b8; line-height: 1.6; }

/* ── State messages ──────────────────────────────────────────────────── */
.gb-msg-info {
    background: #0f1e3a; border: 1px solid #1e3a5f; border-radius: 6px;
    padding: 0.8rem 1.1rem; color: #94a3b8; font-size: 0.83rem;
    display: flex; align-items: flex-start; gap: 0.5rem; line-height: 1.5;
}
.gb-msg-warn {
    background: #2d1f00; border: 1px solid #78450c; border-left: 3px solid #f59e0b;
    border-radius: 6px; padding: 0.8rem 1.1rem; color: #fbbf24; font-size: 0.83rem;
    display: flex; align-items: flex-start; gap: 0.5rem;
}
.gb-msg-error {
    background: #3b0f1a; border: 1px solid #7f1d2e; border-radius: 6px;
    padding: 0.8rem 1.1rem; color: #f87171; font-size: 0.83rem;
}
.gb-msg-success {
    background: #052010; border: 1px solid #134d28; border-radius: 6px;
    padding: 0.65rem 1rem; color: #4ade80; font-size: 0.82rem;
    display: flex; align-items: center; gap: 0.45rem; margin-bottom: 0.7rem;
}

/* ── AI section ──────────────────────────────────────────────────────── */
.gb-ai-divider {
    display: flex; align-items: center; gap: 0.75rem;
    margin: 1.4rem 0 0.9rem;
    color: #4a7fa5; font-size: 0.7rem; font-weight: 700;
    text-transform: uppercase; letter-spacing: 0.1em;
}
.gb-ai-divider::before, .gb-ai-divider::after {
    content: ''; flex: 1; height: 1px; background: #1e3a5f;
}
.gb-ai-label {
    background: #111a2e; border: 1px solid #1e3a5f; border-radius: 4px;
    padding: 0.18rem 0.65rem; white-space: nowrap;
    display: flex; align-items: center; gap: 0.35rem;
}
.gb-model-chip {
    background: #0f2940; border: 1px solid #1e3a5f; border-radius: 5px;
    padding: 0.45rem 0.85rem; font-size: 0.75rem; color: #60a5fa;
    margin-bottom: 0.85rem; font-family: 'JetBrains Mono', monospace;
    display: inline-block;
}
.gb-report-box {
    background: #111a2e; border: 1px solid #1e3a5f; border-radius: 8px;
    padding: 1.2rem 1.4rem; margin-top: 0.85rem; color: #e2e8f0; line-height: 1.65;
}

/* ── Decision controls ───────────────────────────────────────────────── */
.gb-decision-panel {
    background: #111a2e; border: 1px solid #1e3a5f; border-radius: 8px;
    padding: 1rem 1.25rem; margin-bottom: 0.85rem;
}
.gb-decision-field-label {
    font-size: 0.67rem; color: #4a7fa5; text-transform: uppercase;
    letter-spacing: 0.08em; margin-bottom: 0.3rem; font-weight: 600;
}
.gb-decision-field-value { font-size: 0.9rem; color: #e2e8f0; font-weight: 600; }
.gb-sim-note {
    font-size: 0.76rem; color: #64748b;
    padding: 0.35rem 0; margin-bottom: 0.75rem;
    display: flex; align-items: center; gap: 0.4rem;
}
.gb-gate-locked {
    background: #3b0f1a; border: 1px solid #7f1d2e; border-radius: 6px;
    padding: 0.75rem 1rem; color: #f87171; font-size: 0.83rem;
    margin-bottom: 0.75rem; display: flex; align-items: flex-start; gap: 0.4rem;
}
.gb-gate-used {
    background: #0f1e3a; border: 1px solid #1e3a5f; border-radius: 6px;
    padding: 0.75rem 1rem; color: #64748b; font-size: 0.83rem;
    margin-bottom: 0.75rem; display: flex; align-items: flex-start; gap: 0.4rem;
}
.gb-decision-result {
    background: #0f2940; border: 1px solid #1e3a5f; border-radius: 6px;
    padding: 0.85rem 1.15rem; margin: 0.85rem 0;
}
.gb-decision-result .dr-label {
    font-size: 0.67rem; color: #4a7fa5; text-transform: uppercase;
    letter-spacing: 0.08em; margin-bottom: 0.2rem; font-weight: 600;
}
.dr-approved { color: #4ade80; font-weight: 700; font-size: 0.9rem; }
.dr-rejected { color: #f87171; font-weight: 700; font-size: 0.9rem; }

/* ── Audit table ─────────────────────────────────────────────────────── */
.gb-audit-cols {
    grid-template-columns: 160px 90px 100px 90px 55px 260px;
}
.gb-audit-header {
    font-size: 0.7rem; font-weight: 700; text-transform: uppercase;
    letter-spacing: 0.09em; color: #4a7fa5;
    padding-bottom: 0.35rem; border-bottom: 1px solid #1e3a5f;
    margin-bottom: 0.6rem; display: flex; align-items: center; gap: 0.4rem;
}
.gb-audit-empty {
    background: #111a2e; border: 1px solid #1e3a5f; border-radius: 6px;
    padding: 2rem; text-align: center; color: #4a7fa5; font-size: 0.85rem;
}

/* ── Back link button ────────────────────────────────────────────────── */
.gb-back-btn {
    display: inline-flex; align-items: center; gap: 0.4rem;
    background: #111a2e; border: 1px solid #1e3a5f; border-radius: 6px;
    padding: 0.4rem 0.9rem; font-size: 0.8rem; color: #94a3b8;
    cursor: pointer; margin-bottom: 1rem; font-weight: 500;
    transition: border-color 0.15s, color 0.15s;
}
.gb-back-btn:hover { border-color: #3b82f6; color: #60a5fa; }

/* ── Event type cell ─────────────────────────────────────────────────── */
.evt-fail    { color: #f87171; font-weight: 600; }
.evt-success { color: #4ade80; font-weight: 600; }
.evt-ip-unfamiliar { color: #fbbf24; font-family: 'JetBrains Mono', monospace; font-size: 0.78rem; }
.evt-ip-known { color: #94a3b8; font-family: 'JetBrains Mono', monospace; font-size: 0.78rem; }

/* ── Streamlit overrides ─────────────────────────────────────────────── */
button[kind="primary"] {
    background-color: #1d4ed8 !important;
    color: #ffffff !important;
    border: 1px solid #2563eb !important;
    border-radius: 6px !important;
    font-weight: 600 !important;
    transition: background-color 0.15s ease !important;
}
button[kind="primary"]:hover:not(:disabled) {
    background-color: #2563eb !important;
}
button[kind="secondary"] {
    background-color: #111a2e !important;
    color: #e2e8f0 !important;
    border: 1px solid #1e3a5f !important;
    border-radius: 6px !important;
    font-weight: 500 !important;
}
button[kind="secondary"]:hover:not(:disabled) {
    background-color: #1e3a5f !important;
    border-color: #3b82f6 !important;
}
.stTabs [data-baseweb="tab-list"] {
    gap: 0;
    background: #0f2940;
    border-radius: 8px 8px 0 0;
    padding: 0.3rem 0.3rem 0;
    border: 1px solid #1e3a5f;
    border-bottom: none;
}
.stTabs [data-baseweb="tab"] {
    border-radius: 6px 6px 0 0 !important;
    padding: 0.5rem 1.25rem !important;
    font-size: 0.82rem !important;
    font-weight: 600 !important;
    color: #4a7fa5 !important;
    background: transparent !important;
    border: none !important;
}
.stTabs [aria-selected="true"] {
    background: #111a2e !important;
    color: #60a5fa !important;
    border-bottom: 2px solid #3b82f6 !important;
}
.stTabs [data-baseweb="tab-panel"] {
    background: #111a2e;
    border: 1px solid #1e3a5f;
    border-top: none;
    border-radius: 0 0 8px 8px;
    padding: 1.2rem 1.5rem;
}
/* search input */
.stTextInput > div > div > input {
    background: #0f2940 !important;
    border: 1px solid #1e3a5f !important;
    color: #e2e8f0 !important;
    border-radius: 6px !important;
}
/* selectbox */
.stSelectbox > div > div {
    background: #0f2940 !important;
    border: 1px solid #1e3a5f !important;
    border-radius: 6px !important;
    color: #e2e8f0 !important;
}
/* radio in sidebar */
[data-testid="stSidebar"] .stRadio > label { display: none; }
[data-testid="stSidebar"] .stRadio > div { gap: 0.2rem !important; flex-direction: column !important; }
[data-testid="stSidebar"] .stRadio div[role="radiogroup"] > label {
    display: flex !important; align-items: center !important; gap: 0.65rem !important;
    padding: 0.5rem 0.75rem !important; border-radius: 6px !important;
    font-size: 0.86rem !important; font-weight: 500 !important;
    color: #94a3b8 !important; cursor: pointer !important; margin-bottom: 0.15rem !important;
    transition: background 0.12s, color 0.12s !important;
}
[data-testid="stSidebar"] .stRadio div[role="radiogroup"] > label:hover {
    background: #111a2e !important; color: #e2e8f0 !important;
}
[data-testid="stSidebar"] .stRadio div[role="radiogroup"] > label[data-baseweb="radio"]:has(input:checked),
[data-testid="stSidebar"] .stRadio div[role="radiogroup"] [aria-checked="true"] {
    background: #1e3a5f !important; color: #60a5fa !important;
}
[data-testid="stSidebar"] .stRadio [data-testid="stMarkdownContainer"] p {
    font-size: 0.86rem !important;
    font-weight: 500 !important;
    color: #cbd5e1 !important;
    margin: 0 !important;
}
[data-testid="stSidebar"] .stRadio div[role="radiogroup"] > label:hover [data-testid="stMarkdownContainer"] p {
    color: #ffffff !important;
}
[data-testid="stSidebar"] .stRadio div[role="radiogroup"] > label[data-baseweb="radio"]:has(input:checked) [data-testid="stMarkdownContainer"] p,
[data-testid="stSidebar"] .stRadio div[role="radiogroup"] [aria-checked="true"] [data-testid="stMarkdownContainer"] p {
    color: #60a5fa !important;
    font-weight: 600 !important;
}
/* dataframe in dark */
.stDataFrame { background: #111a2e !important; }
</style>
""",
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# SVG icon helpers (inline, no external dep)
# ---------------------------------------------------------------------------
def _icon(path_d: str, size: int = 14) -> str:
    return (
        f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" '
        f'stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" '
        f'style="display:inline-block;vertical-align:middle;flex-shrink:0">'
        f'{path_d}</svg>'
    )


ICON_SHIELD   = _icon('<path d="M12 2L4.5 5.5v5.5c0 4.8 3.2 9.3 7.5 10.5 4.3-1.2 7.5-5.7 7.5-10.5V5.5L12 2z"/>', 16)
ICON_DASH     = _icon('<rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/><rect x="14" y="14" width="7" height="7"/><rect x="3" y="14" width="7" height="7"/>')
ICON_LIST     = _icon('<line x1="8" y1="6" x2="21" y2="6"/><line x1="8" y1="12" x2="21" y2="12"/><line x1="8" y1="18" x2="21" y2="18"/><line x1="3" y1="6" x2="3.01" y2="6"/><line x1="3" y1="12" x2="3.01" y2="12"/><line x1="3" y1="18" x2="3.01" y2="18"/>')
ICON_AUDIT    = _icon('<path d="M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2"/><rect x="8" y="2" width="8" height="4" rx="1"/><path d="M9 12h6"/><path d="M9 16h6"/>')
ICON_DETAIL   = _icon('<circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/>')
ICON_ALERT    = _icon('<circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/>')
ICON_WARN     = _icon('<path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/>')
ICON_CHECK    = _icon('<polyline points="20 6 9 17 4 12"/>')
ICON_CROSS    = _icon('<line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>')
ICON_LOCK     = _icon('<rect x="3" y="11" width="18" height="11" rx="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/>')
ICON_POLICY   = _icon('<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/>')
ICON_SPARKLE  = _icon('<path d="m12 3-1.9 5.8a2 2 0 0 1-1.3 1.3L3 12l5.8 1.9a2 2 0 0 1 1.3 1.3L12 21l1.9-5.8a2 2 0 0 1 1.3-1.3L21 12l-5.8-1.9a2 2 0 0 1-1.3-1.3L12 3z"/>')
ICON_BACK     = _icon('<line x1="19" y1="12" x2="5" y2="12"/><polyline points="12 19 5 12 12 5"/>')
ICON_FLAG     = _icon('<path d="M4 15s1-1 4-1 5 2 8 2 4-1 4-1V3s-1 1-4 1-5-2-8-2-4 1-4 1z"/><line x1="4" y1="22" x2="4" y2="15"/>')
ICON_SCALE    = _icon('<path d="m16 16 3-8 3 8c-.87.65-1.92 1-3 1s-2.13-.35-3-1Z"/><path d="m2 16 3-8 3 8c-.87.65-1.92 1-3 1s-2.13-.35-3-1Z"/><path d="M7 21h10"/><path d="M12 3v18"/><path d="M3 7h2c2 0 5-1 7-2 2 1 5 2 7 2h2"/>')
ICON_INFO     = _icon('<circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/>')
ICON_CLOCK    = _icon('<circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/>')


# ---------------------------------------------------------------------------
# Severity badge HTML
# ---------------------------------------------------------------------------
def severity_badge(severity: str) -> str:
    meta = {
        "HIGH":   ("sev-high",   "●", "HIGH RISK"),
        "MEDIUM": ("sev-medium", "●", "MEDIUM RISK"),
        "LOW":    ("sev-low",    "●", "LOW RISK"),
    }
    cls, dot, label = meta.get(severity, ("sev-info", "●", severity))
    return f'<span class="sev-badge {cls}">{dot} {label}</span>'


def class_badge(severity: str) -> str:
    """Suspicious / Normal classification badge derived from severity."""
    if severity == "LOW":
        return '<span class="sev-badge sev-low">● NORMAL</span>'
    return '<span class="sev-badge sev-high">● SUSPICIOUS</span>'


# ---------------------------------------------------------------------------
# Parse timestamp safely
# ---------------------------------------------------------------------------
def _parse_ts(ts: str) -> datetime | None:
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return None


def _fmt_ts(ts: str) -> str:
    dt = _parse_ts(ts)
    if dt is None:
        return ts
    return dt.strftime("%Y-%m-%d %H:%M UTC")


def _latest_event_time(incident: dict[str, Any]) -> str:
    times = [e["time_utc"] for e in incident.get("events", [])]
    valid = [t for t in times if _parse_ts(t) is not None]
    if not valid:
        return "—"
    return _fmt_ts(max(valid))


# ---------------------------------------------------------------------------
# Classification helper (transparent mapping from engine severity)
# Suspicious = severity HIGH or MEDIUM (risk_score >= 30)
# Normal     = severity LOW           (risk_score < 30)
# High-Risk  = severity HIGH          (risk_score >= 70)
# These thresholds are NOT invented here; they mirror exactly what engine.py
# returns via its `severity` field.
# ---------------------------------------------------------------------------
def is_suspicious(analysis: dict[str, Any]) -> bool:
    return analysis["severity"] in {"HIGH", "MEDIUM"}


def is_high_risk(analysis: dict[str, Any]) -> bool:
    return analysis["severity"] == "HIGH"


# ---------------------------------------------------------------------------
# Session-state helpers
# ---------------------------------------------------------------------------
def initialize_session() -> None:
    st.session_state.setdefault("view", "dashboard")
    st.session_state.setdefault("selected_incident_id", None)
    st.session_state.setdefault("incident_filter", "All")
    st.session_state.setdefault("incident_search", "")
    st.session_state.setdefault("report", None)
    st.session_state.setdefault("report_status", None)
    st.session_state.setdefault("audit", [])
    st.session_state.setdefault("decision", None)
    st.session_state.setdefault("report_context_id", None)
    st.session_state.setdefault("active_report_id", None)
    st.session_state.setdefault("report_sequence", 0)
    st.session_state.setdefault("active_incident_id", None)


def navigate(view: str, incident_id: str | None = None) -> None:
    st.session_state.view = view
    if incident_id is not None:
        if st.session_state.get("active_incident_id") != incident_id:
            st.session_state.active_incident_id = incident_id
            clear_report_state()
        st.session_state.selected_incident_id = incident_id


def clear_report_state() -> None:
    st.session_state.report = None
    st.session_state.report_status = None
    st.session_state.report_context_id = None
    st.session_state.active_report_id = None
    st.session_state.decision = None


def read_api_key() -> str:
    try:
        return str(st.secrets.get("NEBIUS_API_KEY", ""))
    except (FileNotFoundError, AttributeError):
        return os.getenv("NEBIUS_API_KEY", "")


def read_model() -> str:
    try:
        return str(st.secrets.get("NEBIUS_MODEL", configured_model()))
    except (FileNotFoundError, AttributeError):
        return configured_model()


def audit_decision(
    incident: dict[str, Any], decision: str, outcome: str, current_ctx: str
) -> bool:
    record = build_decision_record(
        incident["id"],
        decision,
        outcome,
        st.session_state.report,
        st.session_state.report_context_id,
        current_ctx,
        st.session_state.active_report_id,
        st.session_state.decision,
    )
    if not record:
        return False
    st.session_state.audit.append(record)
    st.session_state.decision = record
    return True


# ---------------------------------------------------------------------------
# Boot: load data
# ---------------------------------------------------------------------------
initialize_session()

try:
    incidents = load_incidents(ROOT / "data" / "incidents.json")
    policies = load_policies(ROOT / "data" / "policies.json")
except DataValidationError as exc:
    st.error("GuardBee could not load its synthetic data safely.")
    st.markdown(
        f'<div class="gb-msg-error">{ICON_ALERT} '
        "The data file has a validation problem. Correct the file and reload the app to continue."
        "</div>",
        unsafe_allow_html=True,
    )
    st.stop()

incident_by_id: dict[str, dict[str, Any]] = {inc["id"]: inc for inc in incidents}

# Pre-compute analysis for every incident (used across dashboard + list)
analyses: dict[str, dict[str, Any]] = {
    inc["id"]: analyze_incident(inc) for inc in incidents
}

# ---------------------------------------------------------------------------
# Sidebar — brand + navigation
# ---------------------------------------------------------------------------
with st.sidebar:
    st.markdown(
        '<div class="gb-sidebar-brand">'
        '<div class="gb-brand-badge">🐝</div>'
        "GuardBee"
        "</div>",
        unsafe_allow_html=True,
    )

    st.markdown('<div class="gb-sidebar-section">Navigation</div>', unsafe_allow_html=True)

    nav_options = {
        "dashboard":  "📊  Dashboard",
        "incidents":  "🛡️  Security Incidents",
        "audit":      "📋  Audit History",
    }
    nav_labels = list(nav_options.values())
    nav_keys   = list(nav_options.keys())

    # Map current view to label index (detail → incidents)
    cur_view = st.session_state.view
    if cur_view not in nav_keys:
        cur_view = "incidents"
    cur_idx = nav_keys.index(cur_view)

    chosen_label = st.radio(
        "Navigation",
        nav_labels,
        index=cur_idx,
        label_visibility="collapsed",
        key="nav_radio",
    )
    chosen_key = nav_keys[nav_labels.index(chosen_label)]
    if chosen_key != st.session_state.view:
        # Only navigate if not going into 'detail' from radio (detail is internal)
        navigate(chosen_key)
        st.rerun()

    # Quick-stats
    total = len(incidents)
    susp  = sum(1 for iid in incident_by_id if is_suspicious(analyses[iid]))
    norm  = total - susp
    high  = sum(1 for iid in incident_by_id if is_high_risk(analyses[iid]))

    st.markdown('<div class="gb-sidebar-section">Quick Stats</div>', unsafe_allow_html=True)
    st.markdown(
        f"""
        <div style="font-size:0.8rem;color:#94a3b8;line-height:2;">
          <span style="color:#f87171;font-weight:700">{high}</span> High-Risk &nbsp;·&nbsp;
          <span style="color:#fbbf24;font-weight:700">{susp}</span> Suspicious<br>
          <span style="color:#4ade80;font-weight:700">{norm}</span> Normal &nbsp;·&nbsp;
          <span style="color:#60a5fa;font-weight:700">{total}</span> Total
        </div>
        """,
        unsafe_allow_html=True,
    )

    audit_count = len(st.session_state.audit)
    if audit_count:
        st.markdown(
            f'<div style="margin-top:0.8rem;font-size:0.75rem;color:#4a7fa5">'
            f'{ICON_AUDIT} {audit_count} simulated decision{"s" if audit_count != 1 else ""} this session'
            f"</div>",
            unsafe_allow_html=True,
        )

    st.markdown(
        '<div class="gb-sidebar-footer">'
        "Synthetic incidents only.<br>"
        "Risk scores are deterministic Python rules — AI does not compute scores.<br>"
        "Audit history resets on session end."
        "</div>",
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# Safety banner (shown on all views)
# ---------------------------------------------------------------------------
st.markdown(
    f'<div class="gb-safety-bar">{ICON_LOCK}&nbsp;'
    "<strong>Demo safety:</strong>&nbsp; GuardBee never changes real accounts, sessions, or systems. "
    "All incidents, accounts, and IP addresses are synthetic. "
    "Audit history is temporary to this browser session only."
    "</div>",
    unsafe_allow_html=True,
)


# ===========================================================================
# VIEW RENDERING
# ===========================================================================

current_view = st.session_state.view


# ---------------------------------------------------------------------------
# Helper: render event timeline
# ---------------------------------------------------------------------------
def render_timeline(incident: dict[str, Any]) -> None:
    known_ips = set(incident.get("known_ips", []))
    try:
        events = sorted(
            incident["events"],
            key=lambda e: (_parse_ts(e["time_utc"]) or datetime.min.replace(tzinfo=timezone.utc)),
        )
    except Exception:
        events = incident["events"]

    header_html = (
        '<div class="gb-table-wrap">'
        '<div class="gb-table-head gb-timeline-cols">'
        "<span>Event ID</span><span>Time (UTC)</span><span>Type</span>"
        "<span>IP Address</span><span>Country</span>"
        "</div>"
    )
    rows_html = ""
    for evt in events:
        is_fail = evt["type"] == "login_failed"
        is_unfamiliar = evt["ip"] not in known_ips
        ts_fmt = _fmt_ts(evt["time_utc"])
        type_cls = "evt-fail" if is_fail else "evt-success"
        type_lbl = ("✕ login_failed" if is_fail else "✓ login_success")
        ip_cls = "evt-ip-unfamiliar" if is_unfamiliar else "evt-ip-known"
        ip_lbl = evt["ip"] + (" ⚑" if is_unfamiliar else "")
        rows_html += (
            f'<div class="gb-table-row gb-timeline-cols">'
            f'<span class="mono">{evt["id"]}</span>'
            f'<span class="mono" style="color:#94a3b8">{ts_fmt}</span>'
            f'<span class="{type_cls}">{type_lbl}</span>'
            f'<span class="{ip_cls}">{ip_lbl}</span>'
            f'<span style="color:#94a3b8">{evt["country"]}</span>'
            f"</div>"
        )
    st.markdown(header_html + rows_html + "</div>", unsafe_allow_html=True)
    if known_ips:
        st.markdown(
            f'<div style="font-size:0.73rem;color:#64748b;margin-top:0.3rem">'
            f"⚑ Unfamiliar IP (not in known IPs: {', '.join(sorted(known_ips))})"
            f"</div>",
            unsafe_allow_html=True,
        )


# ---------------------------------------------------------------------------
# Helper: render rule hits
# ---------------------------------------------------------------------------
def render_rule_hits(analysis: dict[str, Any]) -> None:
    if not analysis["rule_hits"]:
        st.markdown(
            f'<div class="gb-no-rules">{ICON_CHECK} No GuardBee risk rules fired for this synthetic incident.</div>',
            unsafe_allow_html=True,
        )
        return
    for hit in analysis["rule_hits"]:
        evids_html = "".join(
            f'<span class="gb-evid-tag">{eid}</span>' for eid in hit.get("evidence_ids", [])
        ) or "<span style='color:#64748b;font-size:0.75rem'>No linked event IDs</span>"
        border_color = "#ef4444" if hit["points"] >= 30 else "#f59e0b" if hit["points"] >= 10 else "#3b82f6"
        st.markdown(
            f'<div class="gb-rule-card" style="border-left-color:{border_color}">'
            f'<div class="gb-rule-id">{hit["rule_id"]}</div>'
            f'<div class="gb-rule-flag">{hit["flag"]}</div>'
            f'<div class="gb-rule-pts">+{hit["points"]} risk points</div>'
            f'<div class="gb-rule-evids">{evids_html}</div>'
            f"</div>",
            unsafe_allow_html=True,
        )


# ---------------------------------------------------------------------------
# Helper: render policy cards
# ---------------------------------------------------------------------------
def render_policy_cards(matched_policies: list[dict[str, Any]]) -> None:
    for pol in matched_policies:
        score = pol["match_score"]
        bar_pct = min(int(score / 0.5 * 100), 100)
        st.markdown(
            f'<div class="gb-policy-card">'
            f'<div class="gb-policy-id">{pol["id"]}</div>'
            f'<div class="gb-policy-title">{pol["title"]}</div>'
            f'<div class="gb-policy-sim-row">'
            f'<span class="gb-policy-sim-label">TF-IDF similarity</span>'
            f'<div class="gb-policy-sim-bar"><div class="gb-policy-sim-fill" style="width:{bar_pct}%"></div></div>'
            f'<span class="gb-policy-sim-pct">{score:.3f}</span>'
            f"</div>"
            f'<div class="gb-policy-text">{pol["text"]}</div>'
            f"</div>",
            unsafe_allow_html=True,
        )


# ===========================================================================
# VIEW 1 — DASHBOARD
# ===========================================================================
if current_view == "dashboard":
    st.markdown(
        '<div class="gb-topbar">'
        '<div class="gb-topbar-left">'
        f'<div class="gb-topbar-title">{ICON_DASH}&nbsp; Security Overview</div>'
        '<div class="gb-topbar-sub">Synthetic login incident investigation &nbsp;·&nbsp; Deterministic detection</div>'
        "</div>"
        '<div class="gb-topbar-badge">SIMULATION ONLY</div>'
        "</div>",
        unsafe_allow_html=True,
    )

    # Metric cards
    st.markdown(
        f"""
        <div class="gb-metrics-row">
          <div class="gb-metric" style="--accent:#60a5fa">
            <div class="gb-metric-label">Total Incidents</div>
            <div class="gb-metric-value">{total}</div>
            <div class="gb-metric-sub">Synthetic dataset</div>
          </div>
          <div class="gb-metric" style="--accent:#f87171">
            <div class="gb-metric-label">Suspicious</div>
            <div class="gb-metric-value">{susp}</div>
            <div class="gb-metric-sub">Severity HIGH or MEDIUM</div>
          </div>
          <div class="gb-metric" style="--accent:#4ade80">
            <div class="gb-metric-label">Normal</div>
            <div class="gb-metric-value">{norm}</div>
            <div class="gb-metric-sub">Severity LOW</div>
          </div>
          <div class="gb-metric" style="--accent:#ef4444">
            <div class="gb-metric-label">High-Risk</div>
            <div class="gb-metric-value">{high}</div>
            <div class="gb-metric-sub">Severity HIGH (score ≥ 70)</div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Classification note
    st.markdown(
        '<div class="gb-msg-info" style="margin-bottom:1rem">'
        f"{ICON_INFO}&nbsp;"
        "<span><strong>Classification rule:</strong> Suspicious = engine severity HIGH or MEDIUM (risk score ≥ 30). "
        "Normal = severity LOW (risk score &lt; 30). "
        "High-Risk = severity HIGH (risk score ≥ 70). "
        "Thresholds are computed deterministically by <code>engine.py</code> — not by AI.</span>"
        "</div>",
        unsafe_allow_html=True,
    )

    # Severity distribution
    st.markdown(
        f'<div class="gb-section-header">{ICON_LIST}&nbsp; Severity Distribution</div>',
        unsafe_allow_html=True,
    )
    sev_counts: dict[str, int] = {"HIGH": 0, "MEDIUM": 0, "LOW": 0}
    for iid in incident_by_id:
        sev_counts[analyses[iid]["severity"]] += 1

    for sev_label, count, color in [
        ("HIGH", sev_counts["HIGH"], "#ef4444"),
        ("MEDIUM", sev_counts["MEDIUM"], "#f59e0b"),
        ("LOW", sev_counts["LOW"], "#22c55e"),
    ]:
        bar_w = int(count / total * 100) if total else 0
        st.markdown(
            f'<div style="display:flex;align-items:center;gap:0.75rem;margin-bottom:0.5rem;font-size:0.82rem">'
            f'<span style="width:60px;color:{color};font-weight:700">{sev_label}</span>'
            f'<div style="flex:1;height:10px;background:#1e3a5f;border-radius:5px;overflow:hidden">'
            f'<div style="width:{bar_w}%;height:100%;background:{color};border-radius:5px"></div></div>'
            f'<span style="color:#94a3b8;font-family:JetBrains Mono,monospace;font-size:0.78rem">{count}</span>'
            f"</div>",
            unsafe_allow_html=True,
        )

    st.markdown("<div style='height:0.4rem'></div>", unsafe_allow_html=True)

    # Recent incidents table
    st.markdown(
        f'<div class="gb-section-header">{ICON_CLOCK}&nbsp; Recent Incidents</div>',
        unsafe_allow_html=True,
    )

    # Sort incidents by latest event time descending
    def _latest_dt(inc: dict[str, Any]) -> datetime:
        times = [_parse_ts(e["time_utc"]) for e in inc.get("events", [])]
        valid = [t for t in times if t is not None]
        return max(valid) if valid else datetime.min.replace(tzinfo=timezone.utc)

    sorted_incidents = sorted(incidents, key=_latest_dt, reverse=True)

    # Table header
    st.markdown(
        '<div class="gb-table-wrap">'
        '<div class="gb-table-head" style="grid-template-columns:90px 1fr 140px 100px 100px 130px;gap:0.5rem">'
        "<span>ID</span><span>Title</span><span>Account</span>"
        "<span>Severity</span><span>Risk Score</span><span>Latest Event</span>"
        "</div>",
        unsafe_allow_html=True,
    )
    for inc in sorted_incidents:
        a = analyses[inc["id"]]
        latest = _latest_event_time(inc)
        sev_html = severity_badge(a["severity"])
        row_html = (
            f'<div class="gb-table-row" style="grid-template-columns:90px 1fr 140px 100px 100px 130px;gap:0.5rem">'
            f'<span class="mono">{inc["id"]}</span>'
            f'<span style="color:#e2e8f0">{inc["title"]}</span>'
            f'<span class="mono" style="font-size:0.74rem">{inc["account"]}</span>'
            f'<span>{sev_html}</span>'
            f'<span style="font-family:JetBrains Mono,monospace;color:#60a5fa">{a["risk_score"]}/100</span>'
            f'<span style="color:#94a3b8;font-size:0.78rem">{latest}</span>'
            f"</div>"
        )
        # Use a button trigger to navigate
        st.markdown(row_html, unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)

    # Navigate buttons for each incident
    st.markdown('<div style="margin-top:0.5rem">', unsafe_allow_html=True)
    for inc in sorted_incidents:
        a = analyses[inc["id"]]
        if st.button(
            f"Open {inc['id']} — {inc['title']}",
            key=f"dash_open_{inc['id']}",
            use_container_width=True,
        ):
            navigate("detail", inc["id"])
            st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)


# ===========================================================================
# VIEW 2 — SECURITY INCIDENTS
# ===========================================================================
elif current_view == "incidents":
    st.markdown(
        '<div class="gb-topbar">'
        '<div class="gb-topbar-left">'
        f'<div class="gb-topbar-title">{ICON_LIST}&nbsp; Security Incidents</div>'
        '<div class="gb-topbar-sub">Browse and filter the synthetic incident collection</div>'
        "</div>"
        f'<div class="gb-topbar-badge">{total} INCIDENTS</div>'
        "</div>",
        unsafe_allow_html=True,
    )

    # Filter + Search
    col_filter, col_search = st.columns([2, 3])
    with col_filter:
        filter_choice = st.radio(
            "Filter",
            ["All", "Suspicious", "Normal"],
            index=["All", "Suspicious", "Normal"].index(
                st.session_state.get("incident_filter", "All")
            ),
            horizontal=True,
            key="inc_filter_radio",
        )
        st.session_state.incident_filter = filter_choice
    with col_search:
        search_term = st.text_input(
            "Search",
            value=st.session_state.get("incident_search", ""),
            placeholder="Search by ID, title, account, department…",
            key="inc_search_input",
            label_visibility="collapsed",
        )
        st.session_state.incident_search = search_term

    # Apply filter
    def _passes_filter(inc: dict[str, Any]) -> bool:
        a = analyses[inc["id"]]
        if filter_choice == "Suspicious" and not is_suspicious(a):
            return False
        if filter_choice == "Normal" and is_suspicious(a):
            return False
        if search_term:
            q = search_term.lower()
            if not any(
                q in str(inc.get(f, "")).lower()
                for f in ("id", "title", "account", "department")
            ):
                return False
        return True

    filtered = [inc for inc in incidents if _passes_filter(inc)]

    st.markdown(
        f'<div style="font-size:0.78rem;color:#64748b;margin-bottom:0.75rem">'
        f"Showing {len(filtered)} of {total} incident(s)"
        f"</div>",
        unsafe_allow_html=True,
    )

    if not filtered:
        st.markdown(
            f'<div class="gb-msg-info">{ICON_INFO}&nbsp;'
            "No incidents match the current filter or search. Clear the search or select a different filter.</div>",
            unsafe_allow_html=True,
        )
    else:
        # Table header
        col_widths = "90px 1fr 160px 110px 80px 110px 130px"
        st.markdown(
            f'<div class="gb-table-wrap">'
            f'<div class="gb-table-head gb-inc-cols" style="grid-template-columns:{col_widths}">'
            "<span>ID</span><span>Title</span><span>Account</span>"
            "<span>Department</span><span>Score</span><span>Severity</span><span>Classification</span>"
            "</div>",
            unsafe_allow_html=True,
        )
        for inc in filtered:
            a = analyses[inc["id"]]
            sev_html = severity_badge(a["severity"])
            cls_html = class_badge(a["severity"])
            st.markdown(
                f'<div class="gb-table-row gb-inc-cols" style="grid-template-columns:{col_widths}">'
                f'<span class="mono">{inc["id"]}</span>'
                f'<span style="color:#e2e8f0;font-weight:500">{inc["title"]}</span>'
                f'<span class="mono" style="font-size:0.74rem;color:#94a3b8">{inc["account"]}</span>'
                f'<span style="color:#94a3b8">{inc["department"]}</span>'
                f'<span style="font-family:JetBrains Mono,monospace;color:#60a5fa">{a["risk_score"]}/100</span>'
                f"<span>{sev_html}</span>"
                f"<span>{cls_html}</span>"
                f"</div>",
                unsafe_allow_html=True,
            )
        st.markdown("</div>", unsafe_allow_html=True)

        # Open buttons
        st.markdown('<div style="margin-top:0.5rem">', unsafe_allow_html=True)
        for inc in filtered:
            a = analyses[inc["id"]]
            if st.button(
                f"Investigate {inc['id']} — {inc['title']}  [Score: {a['risk_score']}/100]",
                key=f"inc_open_{inc['id']}",
                use_container_width=True,
                type="primary" if is_high_risk(a) else "secondary",
            ):
                navigate("detail", inc["id"])
                st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)


# ===========================================================================
# VIEW 3 — INCIDENT DETAIL
# ===========================================================================
elif current_view == "detail":
    iid = st.session_state.selected_incident_id
    if iid is None or iid not in incident_by_id:
        st.warning("No incident selected. Please choose one from the Security Incidents list.")
        if st.button("← Go to Security Incidents"):
            navigate("incidents")
            st.rerun()
        st.stop()

    incident = incident_by_id[iid]

    # Ensure investigation state is bound to this incident
    if st.session_state.get("active_incident_id") != iid:
        st.session_state.active_incident_id = iid
        clear_report_state()

    analysis = analyses[iid]
    query = " ".join(
        [incident["title"], incident["department"], *analysis["flags"], analysis["suggested_action"]]
    )
    matched_policies = retrieve_policies(query, policies)
    current_ctx = analysis_context_id(incident, analysis, matched_policies)

    sev = analysis["severity"]

    # Topbar
    st.markdown(
        f'<div class="gb-topbar">'
        f'<div class="gb-topbar-left">'
        f'<div class="gb-topbar-title">{ICON_DETAIL}&nbsp; Incident Detail</div>'
        f'<div class="gb-topbar-sub"><span class="mono" style="color:#7dd3fc">{iid}</span>'
        f'&nbsp;·&nbsp;{incident["title"]}</div>'
        f"</div>"
        f"<div>{severity_badge(sev)}</div>"
        f"</div>",
        unsafe_allow_html=True,
    )

    # Back button
    if st.button(f"{ICON_BACK} Back to Security Incidents", key="detail_back"):
        navigate("incidents")
        st.rerun()

    # ── SECTION A: Incident Overview ─────────────────────────────────────
    st.markdown(
        f'<div class="gb-section-header">{ICON_ALERT}&nbsp; A — Incident Overview</div>',
        unsafe_allow_html=True,
    )
    dept = incident["department"]
    dept_html = (
        f'<span class="sev-badge sev-high" style="font-size:0.72rem">{ICON_WARN} {dept} (Sensitive)</span>'
        if dept == "Finance"
        else f'<span style="color:#e2e8f0">{dept}</span>'
    )
    st.markdown(
        f'<div class="gb-info-card">'
        f'<div class="gb-info-fields">'
        f'<div><div class="field-label">Incident ID</div><span class="mono">{incident["id"]}</span></div>'
        f'<div><div class="field-label">Title</div><span class="field-value">{incident["title"]}</span></div>'
        f'<div><div class="field-label">Account</div><span class="mono">{incident["account"]}</span></div>'
        f'<div><div class="field-label">Department</div>{dept_html}</div>'
        f'<div><div class="field-label">Risk Score</div>'
        f'<span style="font-family:JetBrains Mono,monospace;color:#60a5fa;font-weight:700;font-size:1.1rem">'
        f'{analysis["risk_score"]}</span><span style="color:#64748b;font-size:0.8rem">/100</span></div>'
        f'<div><div class="field-label">Severity</div><div style="margin-top:0.15rem">{severity_badge(sev)}</div></div>'
        f'<div><div class="field-label">Classification</div><div style="margin-top:0.15rem">{class_badge(sev)}</div></div>'
        f"</div>"
        f"</div>",
        unsafe_allow_html=True,
    )

    # ── SECTION B: Event Timeline ─────────────────────────────────────────
    st.markdown(
        f'<div class="gb-section-header">{ICON_CLOCK}&nbsp; B — Login Event Timeline / Evidence</div>',
        unsafe_allow_html=True,
    )
    render_timeline(incident)

    # ── SECTION C: Deterministic Threat Analysis ──────────────────────────
    st.markdown(
        f'<div class="gb-section-header">{ICON_ALERT}&nbsp; C — Deterministic Threat Analysis</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div class="gb-msg-info" style="margin-bottom:0.85rem">'
        f"{ICON_INFO}&nbsp;"
        "<span><strong>Deterministic / rule-based analysis.</strong> "
        "These results are computed by <code>engine.py</code> using explicit Python rules — "
        "not by any AI model. Risk scores are fully explainable and repeatable.</span>"
        "</div>",
        unsafe_allow_html=True,
    )
    render_rule_hits(analysis)
    if analysis["evidence_ids"]:
        evids_html = " &nbsp;·&nbsp; ".join(
            f'<span class="gb-evid-tag">{eid}</span>' for eid in analysis["evidence_ids"]
        )
        st.markdown(
            f'<div style="font-size:0.76rem;color:#64748b;margin:-0.2rem 0 0.6rem">All evidence IDs:&nbsp;{evids_html}</div>',
            unsafe_allow_html=True,
        )
    st.markdown(
        f'<div class="gb-rule-card" style="border-left-color:#0ea5e9">'
        f'<div class="field-label" style="font-size:0.67rem;color:#4a7fa5;text-transform:uppercase;letter-spacing:.08em;margin-bottom:.3rem;font-weight:600">Suggested Action</div>'
        f'<div style="color:#e2e8f0;font-weight:600;font-size:0.88rem">{analysis["suggested_action"]}</div>'
        f"</div>",
        unsafe_allow_html=True,
    )

    # ── SECTION D: Retrieved Security Policies ────────────────────────────
    st.markdown(
        f'<div class="gb-section-header">{ICON_POLICY}&nbsp; D — Retrieved Security Policies</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        f'<div class="gb-msg-info" style="margin-bottom:0.85rem">'
        f"{ICON_INFO}&nbsp;"
        f"<span>Retrieved locally using scikit-learn TF-IDF cosine similarity. "
        f"Only passages scoring at least <strong>{DEFAULT_MIN_SIMILARITY:.2f}</strong> are shown. "
        f"These are reference policies for the analyst — they are not instructions for the AI.</span>"
        f"</div>",
        unsafe_allow_html=True,
    )
    if not matched_policies:
        st.markdown(
            f'<div class="gb-msg-warn">{ICON_WARN}&nbsp;'
            "No policy passage met the similarity threshold for this incident. "
            "AI analysis and decision controls are unavailable without valid policy context.</div>",
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            f'<div class="gb-section-header" style="border:none;padding:0;margin-bottom:0.7rem">'
            f"{ICON_POLICY}&nbsp;{len(matched_policies)} Policy Passage{'s' if len(matched_policies) != 1 else ''} Retrieved"
            f"</div>",
            unsafe_allow_html=True,
        )
        render_policy_cards(matched_policies)

    # ── SECTION E: Nemotron AI Explanation ───────────────────────────────
    st.markdown(
        f'<div class="gb-ai-divider"><span class="gb-ai-label">{ICON_SPARKLE}&nbsp;AI-Generated Analysis (Optional)</span></div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        f'<div class="gb-model-chip">Nebius Token Factory &nbsp;·&nbsp; Model: {read_model()}</div>',
        unsafe_allow_html=True,
    )

    if not matched_policies:
        st.markdown(
            f'<div class="gb-msg-warn" style="margin-bottom:0.85rem">{ICON_WARN}&nbsp;'
            "AI explanation is unavailable — no policy context was retrieved for this incident.</div>",
            unsafe_allow_html=True,
        )

    if st.button(
        "🔍 Request Simplified AI Explanation (NVIDIA Nemotron)",
        type="primary",
        disabled=not bool(matched_policies),
        use_container_width=True,
        key="ai_request_btn",
    ):
        clear_report_state()
        try:
            with st.spinner("Calling Nebius Token Factory — GuardBee does not fabricate AI reports…"):
                report = generate_report(
                    read_api_key(), incident, analysis, matched_policies, model=read_model()
                )
            usable, reason = validate_report_citations(
                report,
                [event["id"] for event in incident["events"]],
                [pol["id"] for pol in matched_policies],
            )
            if not usable:
                st.session_state.report_status = reason
            else:
                st.session_state.report = report
                st.session_state.report_status = reason
                st.session_state.report_context_id = current_ctx
                st.session_state.report_sequence += 1
                st.session_state.active_report_id = (
                    f"{current_ctx}:{st.session_state.report_sequence}"
                )
        except AIReportError as exc:
            st.session_state.report_status = str(exc)

    if st.session_state.report:
        st.markdown(
            f'<div class="gb-msg-success">{ICON_CHECK}&nbsp;{st.session_state.report_status}</div>',
            unsafe_allow_html=True,
        )
        st.markdown('<div class="gb-report-box">', unsafe_allow_html=True)
        st.markdown(st.session_state.report)
        st.markdown("</div>", unsafe_allow_html=True)
    elif st.session_state.report_status:
        st.markdown(
            f'<div class="gb-msg-error">{ICON_ALERT}&nbsp;AI report unavailable — '
            f"{st.session_state.report_status}<br>"
            f'<span style="font-size:0.78rem;opacity:0.85">Approval remains disabled. '
            f"Verify the API key, network access, account credits, and configured model name.</span></div>",
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            f'<div class="gb-msg-info" style="margin-top:0.5rem">{ICON_INFO}&nbsp;'
            "Configure a Nebius API key in <code>.streamlit/secrets.toml</code> and click "
            "<strong>Request Simplified AI Explanation</strong> to unlock the human decision controls."
            "</div>",
            unsafe_allow_html=True,
        )

    # ── Approve / Reject ──────────────────────────────────────────────────
    st.markdown(
        f'<div class="gb-section-header" style="margin-top:1.4rem">{ICON_SCALE}&nbsp; Human Approval Gate — Simulation Only</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        f'<div class="gb-decision-panel">'
        f'<div class="gb-decision-field-label">Proposed Simulated Action</div>'
        f'<div class="gb-decision-field-value">{analysis["suggested_action"]}</div>'
        f"</div>",
        unsafe_allow_html=True,
    )
    st.markdown(
        f'<div class="gb-sim-note">{ICON_LOCK}&nbsp;'
        "Simulation only — no real account or security action will be performed.</div>",
        unsafe_allow_html=True,
    )

    can_decide = can_record_decision(
        st.session_state.report,
        st.session_state.report_context_id,
        current_ctx,
        st.session_state.active_report_id,
        st.session_state.decision,
    )

    if not can_decide:
        if st.session_state.decision:
            st.markdown(
                f'<div class="gb-gate-used">{ICON_INFO}&nbsp;'
                "A decision is already recorded for this AI analysis. "
                "Run a new analysis to enable one new simulated decision.</div>",
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                f'<div class="gb-gate-locked">{ICON_LOCK}&nbsp;'
                "Approve and Reject unlock only after a current, citation-validated AI report is available. "
                "Complete the AI analysis step above first.</div>",
                unsafe_allow_html=True,
            )

    col_approve, col_reject = st.columns(2)
    with col_approve:
        if st.button(
            "✓ Approve",
            disabled=not can_decide,
            use_container_width=True,
            key="btn_approve",
            type="primary",
        ):
            ok = audit_decision(
                incident,
                "APPROVED",
                "Simulated session-revocation response recorded; no external system was changed.",
                current_ctx,
            )
            if not ok:
                st.error("Decision gate rejected the record — the report may be stale. Please re-analyse.")
            else:
                st.rerun()
    with col_reject:
        if st.button(
            "✕ Reject",
            disabled=not can_decide,
            use_container_width=True,
            key="btn_reject",
        ):
            ok = audit_decision(
                incident,
                "REJECTED",
                "No action taken; recommendation rejected by demo analyst.",
                current_ctx,
            )
            if not ok:
                st.error("Decision gate rejected the record — the report may be stale. Please re-analyse.")
            else:
                st.rerun()

    if st.session_state.decision:
        d = st.session_state.decision
        result_cls = "dr-approved" if d["decision"] == "APPROVED" else "dr-rejected"
        result_icon = "✓" if d["decision"] == "APPROVED" else "✕"
        st.markdown(
            f'<div class="gb-decision-result">'
            f'<div class="dr-label">Simulated Decision Recorded</div>'
            f'<div class="{result_cls}">{result_icon} {d["decision"]}: {d["outcome"]}</div>'
            f'<div style="font-size:0.74rem;color:#64748b;margin-top:0.3rem">'
            f'Report ID: <span class="mono">{d.get("report_id","—")}</span>'
            f"</div>"
            f"</div>",
            unsafe_allow_html=True,
        )


# ===========================================================================
# VIEW 4 — AUDIT HISTORY
# ===========================================================================
elif current_view == "audit":
    st.markdown(
        '<div class="gb-topbar">'
        '<div class="gb-topbar-left">'
        f'<div class="gb-topbar-title">{ICON_AUDIT}&nbsp; Audit History</div>'
        '<div class="gb-topbar-sub">Simulated session-only decision audit log</div>'
        "</div>"
        f'<div class="gb-topbar-badge">{len(st.session_state.audit)} RECORD(S)</div>'
        "</div>",
        unsafe_allow_html=True,
    )

    st.markdown(
        f'<div class="gb-msg-warn" style="margin-bottom:1rem">{ICON_WARN}&nbsp;'
        "<strong>Demo / simulated audit history.</strong> "
        "These records exist only in this browser session. "
        "They are not durable, not cryptographically signed, and not a production-grade immutable log. "
        "Records reset when the session ends or the page refreshes.</div>",
        unsafe_allow_html=True,
    )

    audit_records: list[dict[str, Any]] = st.session_state.audit

    if not audit_records:
        st.markdown(
            f'<div class="gb-audit-empty">'
            f"{ICON_AUDIT}<br><br>"
            "<strong>No simulated decisions recorded yet.</strong><br>"
            "Investigate an incident, generate a validated AI explanation, then Approve or Reject."
            "</div>",
            unsafe_allow_html=True,
        )
    else:
        # Table
        col_widths = "170px 90px 110px 90px 60px 1fr"
        st.markdown(
            f'<div class="gb-table-wrap">'
            f'<div class="gb-table-head gb-audit-cols" style="grid-template-columns:{col_widths}">'
            "<span>Time (UTC)</span><span>Incident</span><span>Actor</span>"
            "<span>Decision</span><span>Sim?</span><span>Report ID</span>"
            "</div>",
            unsafe_allow_html=True,
        )
        for rec in reversed(audit_records):
            dec = rec.get("decision", "—")
            dec_badge = (
                '<span class="sev-badge sev-low">✓ APPROVED</span>'
                if dec == "APPROVED"
                else '<span class="sev-badge sev-high">✕ REJECTED</span>'
            )
            sim_badge = (
                '<span class="sev-badge sev-info">SIM</span>'
                if rec.get("simulation_only")
                else "<span>—</span>"
            )
            ts_val = rec.get("time_utc", "—")
            rid = rec.get("report_id", "—")
            iid_rec = rec.get("incident_id", "—")
            st.markdown(
                f'<div class="gb-table-row gb-audit-cols" style="grid-template-columns:{col_widths}">'
                f'<span class="mono" style="font-size:0.74rem;color:#94a3b8">{ts_val}</span>'
                f'<span class="mono">{iid_rec}</span>'
                f'<span style="color:#94a3b8">{rec.get("actor","—")}</span>'
                f"<span>{dec_badge}</span>"
                f"<span>{sim_badge}</span>"
                f'<span class="mono" style="font-size:0.68rem;color:#4a7fa5;word-break:break-all">{rid}</span>'
                f"</div>",
                unsafe_allow_html=True,
            )
        st.markdown("</div>", unsafe_allow_html=True)

        # Navigate to incident from audit row
        st.markdown(
            f'<div style="margin-top:0.6rem;font-size:0.78rem;color:#64748b;margin-bottom:0.5rem">'
            "Click a button below to navigate to the corresponding incident:</div>",
            unsafe_allow_html=True,
        )
        seen_ids: set[str] = set()
        for rec in reversed(audit_records):
            iid_rec = rec.get("incident_id", "")
            if iid_rec and iid_rec in incident_by_id and iid_rec not in seen_ids:
                seen_ids.add(iid_rec)
                inc = incident_by_id[iid_rec]
                if st.button(
                    f"Open {iid_rec} — {inc['title']}",
                    key=f"audit_open_{iid_rec}",
                    use_container_width=True,
                ):
                    navigate("detail", iid_rec)
                    st.rerun()

    st.markdown(
        f'<div style="font-size:0.74rem;color:#4a7fa5;margin-top:1rem">'
        f"{ICON_INFO}&nbsp;This audit history is in-memory only and resets when the browser session ends or refreshes."
        f"</div>",
        unsafe_allow_html=True,
    )
