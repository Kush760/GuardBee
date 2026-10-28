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

import altair as alt
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
ASSETS = ROOT / "assets"
st.set_page_config(
    page_title="GuardBee | Security Analytics Console",
    page_icon=str(ASSETS / "guardbee_shield.png"),
    layout="wide",
    initial_sidebar_state="auto",  # expanded on desktop, collapsed on phones so it never covers the page
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
# Same hues as the tone-* card values; green stays reserved for the NORMAL classification.
SEVERITY_HEX = {"HIGH": "#DC2626", "MEDIUM": "#D97706", "LOW": "#2563EB", "Not assigned": "#64748B"}
CLASSIFICATION_HEX = {"SUSPICIOUS": "#DC2626", "NORMAL": "#16A34A", "INSUFFICIENT_EVIDENCE": "#D97706"}
# Markdown colour names for legend dots, matched to the chart hues above.
LEGEND_DOTS = {"#DC2626": "red", "#16A34A": "green", "#D97706": "orange", "#2563EB": "blue", "#64748B": "gray"}
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
/* Collapsed sidebar: the top bar shows the logo icon, so give it a surface and push content below it. */
.stApp:has([data-testid="stSidebar"][data-collapsed="true"]) [data-testid="stHeader"] {
  background: rgba(244, 247, 252, 0.94); backdrop-filter: blur(6px); border-bottom: 1px solid var(--gb-border); }
.stApp:has([data-testid="stSidebar"][data-collapsed="true"]) [data-testid="stMainBlockContainer"] { padding-top: 5rem; }
h1, h2, h3, h4 { color: var(--gb-text); letter-spacing: -0.01em; }
h1 { font-weight: 750 !important; font-size: 2.1rem !important; padding: 0 0 0.15rem !important; }
[data-testid="stMain"] [data-testid="stAlert"] [data-testid="stMarkdownContainer"] p { font-size: 0.92rem; }

/* Dashboard (mockup layout) */
[class*="st-key-dash-"] h3 { font-size: 1.05rem !important; font-weight: 700; padding: 0 0 0.25rem !important; }
[data-testid="stMain"] [class*="st-key-tone-"] { min-height: 132px; }
[class*="st-key-tone-"][class*="-kpi-"] { position: relative; padding-left: 3.9rem !important; min-height: 176px; }
[class*="st-key-tone-"][class*="-kpi-"] [data-testid="stMetricLabel"] p { text-transform: none; letter-spacing: 0;
  font-size: 0.8rem; font-weight: 700; }
[class*="st-key-kpi-icon-"] { position: absolute !important; left: 1rem; top: 1.1rem; width: 38px !important;
  height: 38px; border-radius: 50%; display: flex; align-items: center; justify-content: center; }
[class*="st-key-kpi-icon-"] { gap: 0 !important; padding: 0 !important; }
[class*="st-key-kpi-icon-"] > div { width: auto !important; }
[class*="st-key-kpi-icon-"] [data-testid="stMarkdownContainer"], [class*="st-key-kpi-icon-"] p { margin: 0 !important; line-height: 1; }
[class*="st-key-kpi-icon-"] span[role="img"] { font-size: 1.3rem; color: inherit; }
[class*="st-key-kpi-icon-red"] { background: #FECACA; color: #DC2626; }
[class*="st-key-tone-red-kpi"] [data-testid="stMetricLabel"] p { color: #DC2626; }
[class*="st-key-kpi-icon-green"] { background: #BBF7D0; color: #16A34A; }
[class*="st-key-tone-green-kpi"] [data-testid="stMetricLabel"] p { color: #16A34A; }
[class*="st-key-kpi-icon-amber"] { background: #FDE68A; color: #B45309; }
[class*="st-key-tone-amber-kpi"] [data-testid="stMetricLabel"] p { color: #D97706; }
[class*="st-key-kpi-icon-blue"] { background: #BFDBFE; color: #2563EB; }
[class*="st-key-tone-blue-kpi"] [data-testid="stMetricLabel"] p { color: #2563EB; }
[class*="st-key-kpi-icon-violet"] { background: #DDD6FE; color: #6D28D9; }
[class*="st-key-tone-violet-kpi"] [data-testid="stMetricLabel"] p { color: #6D28D9; }
.st-key-dash-overview, .st-key-dash-recent { min-height: 318px; }
.st-key-dash-thead { border-bottom: 1px solid var(--gb-border); }
.st-key-dash-thead [data-testid="stCaptionContainer"] { font-weight: 600; text-transform: uppercase;
  letter-spacing: 0.04em; font-size: 0.72rem; }
[class*="st-key-dash-row-"] { border-bottom: 1px solid #EEF2F7; padding: 0.1rem 0 0.35rem; }
[class*="st-key-dash-row-"] p { font-size: 0.86rem; margin-bottom: 0; }
[class*="st-key-dash_view_"] button { min-height: 1.9rem; padding: 0.1rem 0.5rem; font-size: 0.8rem; }
.st-key-dash_view_all button { background: transparent; border: none; color: var(--gb-accent);
  box-shadow: none; justify-content: flex-end; }
.st-key-dash-source { background: #EEF4FF !important; border-color: #C7D7FE !important; }
.st-key-dash-source { padding: 0.7rem 1rem !important; }
.st-key-dash-source [data-testid="stMarkdownContainer"] { margin-bottom: 0 !important; }
.st-key-dash-source p { margin: 0; font-size: 0.88rem; color: #1E3A8A; }

/* Security Incidents (mockup layout) */
.st-key-incident_picker [role="radiogroup"] { gap: 0.5rem; width: 100%; }
.st-key-incident_picker [role="radiogroup"] > div { width: 100%; padding: 0.55rem 0.75rem;
  background: #FFFFFF; border: 1px solid var(--gb-border); border-radius: 10px; }
.st-key-incident_picker [role="radiogroup"] > div:hover { border-color: #C7D2FE; }
.st-key-incident_picker [role="radiogroup"] > div:has([data-selected="true"]) { background: #EEF2FF;
  border-color: #A5B4FC; box-shadow: inset 3px 0 0 var(--gb-accent); }
.st-key-incident_picker [data-testid="stRadioOption"] { width: 100%; cursor: pointer; }
.st-key-incident_picker [data-testid="stRadioOption"] > div > div:first-child { display: none; }
.st-key-incident_picker [data-testid="stRadioOption"] p { font-size: 0.88rem; }
.st-key-incident_picker [data-testid="stCaptionContainer"] p { font-size: 0.78rem; }
[class*="st-key-inc-"] h3 { font-size: 1.25rem !important; padding: 0 !important; }
[class*="st-key-tl-"] p { font-size: 0.88rem; margin-bottom: 0; }
[class*="st-key-tl-"] [data-testid="stMarkdownContainer"] { margin-bottom: 0 !important; }
.st-key-inc-engine li { margin-bottom: 0.15rem; font-size: 0.9rem; }
.st-key-inc-engine li p { margin: 0; }
.st-key-inc-basic [data-testid="stCaptionContainer"] p { margin-bottom: 0; font-size: 0.75rem; }
.st-key-inc-engine { background: #F8FAFF !important; }
.st-key-inc-policies, .st-key-inc-decision { min-height: 190px; }

/* Security Incidents: compact cards, icon chips, connected timeline, hover feedback */
[class*="-kpi-c-"] { min-height: 0 !important; padding: 0.75rem 0.9rem 0.75rem 3.7rem !important; }
[class*="-kpi-c-"] [class*="st-key-kpi-icon-"] { top: 50%; transform: translateY(-50%); }
[class*="-kpi-c-"] [data-testid="stMetricValue"] { font-size: 1.3rem; }
.st-key-incident_picker [data-testid="stRadioOption"] p .stMarkdownColoredText:first-child,
.st-key-inc-header h3 .stMarkdownColoredText:first-child {
  display: inline-flex; align-items: center; justify-content: center; vertical-align: middle;
  background: color-mix(in srgb, currentColor 14%, white); }
.st-key-incident_picker [data-testid="stRadioOption"] p .stMarkdownColoredText:first-child {
  width: 1.7rem; height: 1.7rem; border-radius: 8px; margin-right: 0.35rem; }
.st-key-inc-header h3 .stMarkdownColoredText:first-child { width: 2.5rem; height: 2.5rem; border-radius: 12px;
  margin-right: 0.6rem; }
.st-key-inc-header h3 span[role="img"] { font-size: 1.5rem; }
.st-key-incident_picker [role="radiogroup"] > div { transition: transform .15s ease, box-shadow .15s ease,
  border-color .15s ease, background .15s ease; }
.st-key-incident_picker [role="radiogroup"] > div:hover { transform: translateX(3px);
  box-shadow: 0 6px 16px rgba(79, 70, 229, 0.10); }
[data-testid="stMain"] [class*="st-key-tone-"], [data-testid="stMain"] [class*="st-key-inc-"],
[data-testid="stMain"] [class*="st-key-dash-"] { transition: transform .18s ease, box-shadow .18s ease; }
[data-testid="stMain"] [class*="st-key-tone-"]:hover { transform: translateY(-2px);
  box-shadow: 0 12px 26px rgba(20, 33, 61, 0.08); }
[data-testid="stMain"] [class*="st-key-inc-"]:hover, [data-testid="stMain"] [class*="st-key-dash-"]:hover {
  box-shadow: 0 10px 24px rgba(20, 33, 61, 0.06); }
[data-testid="stMain"] button { transition: transform .15s ease, box-shadow .15s ease, filter .15s ease; }
[data-testid="stMain"] button:not(:disabled):hover { transform: translateY(-1px); }
[data-testid="stMain"] .st-key-ai_request_btn button, [data-testid="stMain"] .st-key-engine_full_report button {
  background: #EEF2FF; color: var(--gb-accent); border: 1px solid #C7D2FE; }
[data-testid="stMain"] .st-key-ai_request_btn button:not(:disabled):hover,
[data-testid="stMain"] .st-key-engine_full_report button:hover { background: #E0E7FF; border-color: #A5B4FC; }
[data-testid="stMain"] .st-key-btn_approve button:disabled { background: #16A34A; color: #FFFFFF; opacity: 0.35; }
[data-testid="stMain"] .st-key-btn_reject button:disabled { background: #DC2626; color: #FFFFFF; opacity: 0.35; }
.st-key-timeline { gap: 0 !important; }
[class*="st-key-tl-"] { border-radius: 8px; padding: 0.5rem 0.4rem !important; }
[class*="st-key-tl-"]:hover { background: #EEF2FF; }
[class*="st-key-tl-"] [data-testid="stColumn"]:nth-child(2) { position: relative; align-self: stretch;
  display: flex; align-items: center; justify-content: center; }
[class*="st-key-tl-"] [data-testid="stColumn"]:nth-child(2)::before { content: ""; position: absolute;
  left: 50%; top: -0.5rem; bottom: -0.5rem; width: 2px; margin-left: -1px; background: #E2E8F0; }
[class*="st-key-tl-"] [data-testid="stColumn"]:nth-child(2) span[role="img"] { position: relative; z-index: 1;
  background: var(--gb-bg); border-radius: 50%; font-size: 1.1rem; }

/* Sidebar */
[data-testid="stSidebar"] {
  background: linear-gradient(180deg, #0B1220 0%, #0F1730 45%, #1A1E4A 80%, #2B2675 100%);
  border-right: 1px solid #1E293B; }
@media (min-width: 768px) {
  [data-testid="stSidebar"]:not([data-collapsed="true"]) { min-width: 248px !important; max-width: 248px !important; } }
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
/* Navigation at the top, cards pinned to the bottom, slim scrollbar */
[data-testid="stSidebarContent"] { display: flex; flex-direction: column;
  scrollbar-width: thin; scrollbar-color: rgba(255, 255, 255, 0.16) transparent; }
[data-testid="stSidebarContent"]::-webkit-scrollbar { width: 6px; }
[data-testid="stSidebarContent"]::-webkit-scrollbar-track { background: transparent; }
[data-testid="stSidebarContent"]::-webkit-scrollbar-thumb { background: rgba(255, 255, 255, 0.16); border-radius: 6px; }
[data-testid="stSidebarUserContent"] { margin-top: auto; padding-top: 1rem !important; padding-bottom: 1rem !important; }
[data-testid="stSidebarUserContent"] [data-testid="stVerticalBlock"] { gap: 0.75rem; }
[data-testid="stSidebar"] .st-key-sidebar-ai, [data-testid="stSidebar"] .st-key-sidebar-demo { gap: 0.4rem !important; }
[data-testid="stSidebar"] .st-key-sidebar-ai { background: rgba(255, 255, 255, 0.04) !important;
  border: 1px solid rgba(255, 255, 255, 0.09) !important; border-radius: 12px; }
[data-testid="stSidebar"] .st-key-sidebar-ai [data-testid="stCaptionContainer"] p,
[data-testid="stSidebar"] .st-key-sidebar-demo [data-testid="stCaptionContainer"] p { font-size: 0.8rem; line-height: 1.45; }
[data-testid="stSidebar"] .st-key-sidebar-ai [data-testid="stCaptionContainer"],
[data-testid="stSidebar"] .st-key-sidebar-demo [data-testid="stCaptionContainer"] { margin-bottom: -0.35rem; }
[data-testid="stSidebarUserContent"] > div > [data-testid="stVerticalBlock"] > [data-testid="stElementContainer"]:last-child
  [data-testid="stCaptionContainer"] p { color: #64748B; font-size: 0.75rem; text-align: center; }
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

/* Full-report dialog: compact text so the report stays short */
[data-testid="stDialog"] [data-testid="stVerticalBlock"] [data-testid="stMarkdownContainer"] p,
[data-testid="stDialog"] [data-testid="stVerticalBlock"] [data-testid="stMarkdownContainer"] li {
  font-size: 0.86rem; line-height: 1.45; }
[data-testid="stDialog"] [data-testid="stVerticalBlock"] [data-testid="stMarkdownContainer"] li { margin-bottom: 0.1rem; }
[data-testid="stDialog"] [data-testid="stVerticalBlockBorderWrapper"] { padding: 0.65rem 0.8rem; }
.st-key-report-scroll { max-height: min(440px, calc(100vh - 260px)); overflow-y: auto; overscroll-behavior: contain;
  padding-right: 0.4rem; border-top: 1px solid var(--gb-border); border-bottom: 1px solid var(--gb-border);
  padding-top: 0.6rem; padding-bottom: 0.6rem; scrollbar-width: none; }
.st-key-report-scroll::-webkit-scrollbar { display: none; }  /* still scrolls by wheel, touch, and keyboard */

/* Responsive layout: rows react to the width of the content area (sidebar excluded), not the window. */
[data-testid="stMainBlockContainer"],
.st-key-layout-incidents > * > [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:last-child {
  container-type: inline-size; }
[class*="st-key-layout-"] > * > [data-testid="stHorizontalBlock"],
.st-key-inc-header > * > [data-testid="stHorizontalBlock"],
.st-key-inc-basic > * > [data-testid="stHorizontalBlock"] { flex-wrap: wrap; }
/* Timeline rows and the recent-incidents table keep their columns side by side at every width. */
[class*="st-key-tl-"] > * > [data-testid="stHorizontalBlock"],
.st-key-layout-table [data-testid="stHorizontalBlock"] { flex-wrap: nowrap !important; }
[class*="st-key-tl-"] > * > [data-testid="stHorizontalBlock"] > [data-testid="stColumn"],
.st-key-layout-table [data-testid="stColumn"] { min-width: 0 !important; }
[data-testid="stMain"] button p { white-space: nowrap; }
@container (max-width: 900px) {
  .st-key-layout-kpis > * > [data-testid="stHorizontalBlock"] > [data-testid="stColumn"] {
    flex: 1 1 calc(33.333% - 1rem) !important; min-width: calc(33.333% - 1rem) !important; }
  [class*="st-key-tone-"][class*="-kpi-"] { min-height: 150px; }
}
@container (max-width: 860px) {
  .st-key-layout-split > * > [data-testid="stHorizontalBlock"] > [data-testid="stColumn"],
  .st-key-layout-incidents > * > [data-testid="stHorizontalBlock"] > [data-testid="stColumn"] {
    flex: 1 1 100% !important; min-width: 100% !important; }
  .st-key-dash-overview, .st-key-dash-recent { min-height: 0; }
  /* Stacked incident list becomes a swipeable row of cards above the investigation. */
  .st-key-incident_picker [role="radiogroup"] { flex-direction: row; flex-wrap: nowrap; overflow-x: auto;
    padding: 0.1rem 0.1rem 0.5rem; scroll-snap-type: x proximity; }
  .st-key-incident_picker [role="radiogroup"] > div { flex: 0 0 240px; width: 240px; scroll-snap-align: start; }
  .st-key-incident_picker [role="radiogroup"] > div:hover { transform: none; }
}
@container (max-width: 680px) {
  .st-key-layout-toolbar > * > [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:first-child,
  .st-key-layout-timeline > * > [data-testid="stHorizontalBlock"] > [data-testid="stColumn"],
  [class*="st-key-layout-findings-"] > * > [data-testid="stHorizontalBlock"] > [data-testid="stColumn"],
  .st-key-layout-pair > * > [data-testid="stHorizontalBlock"] > [data-testid="stColumn"] {
    flex: 1 1 100% !important; min-width: 100% !important; }
  .st-key-layout-toolbar > * > [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:nth-child(2) {
    flex: 2 1 0 !important; min-width: 0 !important; }
  .st-key-layout-toolbar > * > [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:nth-child(3) {
    flex: 1 1 0 !important; min-width: 110px !important; }
  .st-key-inc-basic > * > [data-testid="stHorizontalBlock"] > [data-testid="stColumn"] {
    flex: 1 1 calc(50% - 1rem) !important; min-width: calc(50% - 1rem) !important; }
  .st-key-inc-policies, .st-key-inc-decision { min-height: 0; }
}
@container (max-width: 560px) {
  .st-key-layout-kpis > * > [data-testid="stHorizontalBlock"] > [data-testid="stColumn"] {
    flex: 1 1 calc(50% - 1rem) !important; min-width: calc(50% - 1rem) !important; }
  .st-key-inc-header > * > [data-testid="stHorizontalBlock"] > [data-testid="stColumn"] {
    flex: 1 1 100% !important; min-width: 100% !important; }
}
@container (max-width: 540px) {
  /* Recent incidents: keep ID, score, severity and View; the incident page shows the rest. */
  .st-key-layout-table [data-testid="stColumn"]:nth-child(2),
  .st-key-layout-table [data-testid="stColumn"]:nth-child(5) { display: none; }
}
@container (max-width: 460px) {
  .st-key-layout-inc-kpis > * > [data-testid="stHorizontalBlock"] > [data-testid="stColumn"] {
    flex: 1 1 100% !important; min-width: 100% !important; }
  [class*="st-key-tone-"][class*="-kpi-"]:not([class*="-kpi-c-"]) { min-height: 0; }
}
@media (max-width: 640px) {
  [data-testid="stMainBlockContainer"] { padding-left: 1rem; padding-right: 1rem; }
  h1 { font-size: 1.6rem !important; }
}
</style>
"""

_MARKDOWN_SPECIAL = re.compile(r"([\\`*_{}\[\]()#+\-.!|<>~$:@])")


def md(value: Any) -> str:
    """Escape Markdown so data text is always shown literally."""
    return _MARKDOWN_SPECIAL.sub(r"\\\1", str(value))


_REPORT_IMAGE = re.compile(r"!\[([^\]]*)\]\([^)]*\)")
_REPORT_LINK = re.compile(r"\[([^\]]+)\]\([^)]*\)")
_REPORT_ADDRESS = re.compile(r"(?i)\b(?:https?://|www\.)[^\s`<>]+|[\w.+-]+@[\w-]+(?:\.[\w-]+)+")


def report_markdown(report: str) -> str:
    """Keep the model's headings and lists but never render its links, images, or auto-links."""
    text = _REPORT_IMAGE.sub(r"\1", report)
    text = _REPORT_LINK.sub(r"\1", text)
    text = _REPORT_ADDRESS.sub(lambda match: code(match.group(0)), text)  # code spans never become links
    return text.replace("<", "\\<")


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
def page_header(title: str, subtitle: str, description: str = "") -> None:
    st.title(title)
    st.caption(f"**{subtitle}** · {description}" if description else f"**{subtitle}**")


def card(parent: Any = st, key: str | None = None) -> Any:
    """Bordered card; a key adds an st-key-* class that the stylesheet can tint."""
    if key and CONTAINER_TAKES_KEY:
        return parent.container(border=True, key=key)
    return parent.container(border=True)


def empty_state(message: str, icon: str = "ℹ️") -> None:
    with st.container(border=True):
        st.info(message, icon=icon)


def render_sidebar() -> None:
    with st.sidebar:
        with card(st, "sidebar-demo"):
            st.markdown("**:material/info: Demo only**")
            st.caption("Synthetic incidents and simulated decisions. No live monitoring or real account actions.")
        with card(st, "sidebar-ai"):
            st.markdown("**:material/auto_awesome: AI provider**")
            if read_api_key():
                st.caption(":green[●] Nebius API key configured")
            else:
                st.caption(":orange[●] No Nebius API key — AI reports will show an error")
            st.caption(f"Model · {md(read_model())}")
            st.caption(f"Simulated decisions this session · **{len(st.session_state.audit)}**")
        st.caption(":material/shield: GuardBee · Synthetic demo")


# ---------------------------------------------------------------------------
# Data
# ---------------------------------------------------------------------------
initialize_session()
st.html(STYLES)
logo = ASSETS / "guardbee_logo.svg"
if logo.exists():
    st.logo(str(logo), size="large", icon_image=str(ASSETS / "guardbee_shield.png"))

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
def keyed(parent: Any, key: str) -> Any:
    """Unbordered container with an st-key-* class for the stylesheet (plain on older Streamlit)."""
    return parent.container(key=key) if CONTAINER_TAKES_KEY else parent.container()


def slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")


def percent(count: int) -> str:
    return f"{count / len(incidents):.1%}"


def kpi_card(
    column: Any, label: str, value: Any, caption: str, tone: str, icon: str, help_text: str | None = None,
    compact: bool = False,
) -> None:
    """Status card with a round icon; compact cards fold the caption into the tooltip."""
    with card(column, f"tone-{tone}-kpi-{'c-' if compact else ''}{slug(label)}"):
        with keyed(st, f"kpi-icon-{tone}-{slug(label)}"):
            st.markdown(f":material/{icon}:")
        if compact:
            st.metric(label, value, help=f"{caption}. {help_text}" if help_text else caption)
        else:
            st.metric(label, value, help=help_text)
            st.caption(caption)


def overview_donut(groups: list[tuple[str, int, str]]) -> None:
    """Donut of engine counts with the total in the middle; the legend beside it carries the labels."""
    rows = [{"Group": name, "Count": count} for name, count, _ in groups]
    arcs = (
        alt.Chart(alt.Data(values=rows))
        .mark_arc(innerRadius=56, outerRadius=82, stroke="#FFFFFF", strokeWidth=2)
        .encode(
            theta=alt.Theta("Count:Q", stack=True),
            color=alt.Color(
                "Group:N",
                scale=alt.Scale(domain=[name for name, _, _ in groups], range=[hex_ for _, _, hex_ in groups]),
                legend=None,
            ),
            tooltip=["Group:N", "Count:Q"],
        )
    )
    centre = alt.Chart(alt.Data(values=[{"total": str(len(incidents)), "label": "Total incidents"}]))
    total = centre.mark_text(fontSize=26, fontWeight=700, color="#14213D", dy=-8).encode(text="total:N")
    label = centre.mark_text(fontSize=11, color="#64748B", dy=14).encode(text="label:N")
    st.altair_chart((arcs + total + label).properties(height=190).configure_view(stroke=None))


def dashboard_page() -> None:

    # Row 1: KPI cards
    with keyed(st, "layout-kpis"):
        cards = st.columns(5, gap="small")
    kpi_card(cards[0], "Total valid incidents", len(incidents), "From dataset", "blue", "verified_user")
    for column, key, icon in zip(
        cards[1:4], ("SUSPICIOUS", "NORMAL", "INSUFFICIENT_EVIDENCE"), ("gpp_maybe", "gpp_good", "help")
    ):
        if any_classified:
            count = sum(1 for analysis in analyses.values() if classification_of(analysis) == key)
            value, caption = count, percent(count)
            label = key.replace("_", " ").title()
        else:
            value, caption = "—", "Not classified yet"
            label = key.replace("_", " ").capitalize()
        kpi_card(column, label, value, caption, CLASSIFICATION_TONES[key], icon)
    kpi_card(
        cards[4], "Rejected records", 0, "Fail-closed loader", "violet", "report",
        help_text="Every record must pass validation or loading stops, so a loaded dataset has no rejected "
        "records. Partial processing is not implemented yet.",
    )

    # Row 2: overview donut and recent incidents
    with keyed(st, "layout-split"):
        left, right = st.columns([5, 7], gap="small")
    with card(left, "dash-overview"):
        st.subheader("Incident Overview")
        if any_classified:
            groups = [
                (
                    key.replace("_", " ").title(),
                    sum(1 for analysis in analyses.values() if classification_of(analysis) == key),
                    hex_,
                )
                for key, hex_ in CLASSIFICATION_HEX.items()
            ]
            st.caption("By classification from engine.py")
        else:
            groups = [
                (name.title() if name != NOT_ASSIGNED else name,
                 sum(1 for analysis in analyses.values() if severity_text(analysis) == name), hex_)
                for name, hex_ in SEVERITY_HEX.items()
            ]
            groups = [group for group in groups if group[1] or group[0] != NOT_ASSIGNED]
            st.caption("By severity — engine.py does not classify yet, and GuardBee never infers a class.")
        chart, legend = st.columns([1, 1], vertical_alignment="center")
        with chart:
            overview_donut(groups)
        with legend:
            for name, count, hex_ in groups:
                dot = LEGEND_DOTS.get(hex_, "gray")
                st.markdown(f":{dot}[●] {name} · **{count}** ({percent(count)})")

    with card(right, "dash-recent"):
        st.subheader("Recent Incidents")
        recent = sorted(incidents, key=latest_event_time, reverse=True)[:5]
        widths = [1.5, 2.3, 1, 1.6, 1.2, 1.3]
        table = keyed(st, "layout-table")  # scrolls sideways on narrow screens instead of crushing columns
        with keyed(table, "dash-thead"):
            for column, heading in zip(
                st.columns(widths, vertical_alignment="center"),
                ("ID", "Classification", "Score", "Severity", "Priority", ""),
            ):
                column.caption(heading)
        for incident in recent:
            analysis = analyses[incident["id"]]
            with keyed(table, f"dash-row-{slug(incident['id'])}"):
                row = st.columns(widths, vertical_alignment="center")
                row[0].markdown(f"**{md(incident['id'])}**")
                row[1].markdown(classification_badge(analysis))
                row[2].markdown(f"**{analysis['risk_score']}**")
                row[3].markdown(severity_badge(analysis))
                priority = analysis.get("investigation_priority")
                row[4].markdown(f":violet-background[{md(priority)}]" if priority else "—")
                if row[5].button("View", key=f"dash_view_{incident['id']}"):
                    go_to_incident(incident["id"])
        _, more = st.columns([3, 1])
        if more.button("View All →", key="dash_view_all"):
            st.switch_page(INCIDENTS_PAGE)

    # Row 3: data source strip
    with card(st, "dash-source"):
        st.markdown(
            ":blue[:material/info:] **Data Source:** Static synthetic JSON file (data/incidents.json)"
            " · Not real-time monitoring"
        )


# ---------------------------------------------------------------------------
# Page 2 - Security Incidents
# ---------------------------------------------------------------------------
def incident_tone(analysis: dict[str, Any]) -> str:
    """Card/icon tone from the engine's class when present, otherwise from its severity."""
    classification = classification_of(analysis)
    if classification:
        return CLASSIFICATION_TONES[classification]
    return SEVERITY_TONES.get(analysis.get("severity") or "", "violet")


def tone_icon(analysis: dict[str, Any]) -> str:
    colour = {"red": "red", "green": "green", "amber": "orange", "blue": "blue"}.get(incident_tone(analysis), "violet")
    icon = "gpp_good" if classification_of(analysis) == "NORMAL" else "gpp_maybe"
    return f":{colour}[:material/{icon}:]"


def short_time(value: str) -> str:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).strftime("%b %d, %H:%M")


def matches_filter(incident: dict[str, Any], option: str) -> bool:
    wanted = INCIDENT_FILTERS.get(option)
    analysis = analyses[incident["id"]]
    return wanted is None or analysis.get("severity") == wanted or classification_of(analysis) == wanted


def filtered_incidents() -> list[dict[str, Any]]:
    option = st.session_state.get("incident_filter", "All")
    query = st.session_state.get("incident_search", "").strip().lower()
    return [
        incident
        for incident in incidents
        if matches_filter(incident, option)
        and (not query or any(query in str(incident[field]).lower() for field in ("id", "title", "account", "department")))
    ]


def render_incident_list(shown: list[dict[str, Any]]) -> str | None:
    with card(st, "inc-list"):
        st.markdown(f"**Incidents ({len(shown)})**")
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
                f"{tone_icon(analyses[identifier])} **{identifier}**  \n{md(incident_by_id[identifier]['title'])}"
            ),
            captions=[
                f"{classification_badge(analyses[identifier])} · {analyses[identifier]['risk_score']} · "
                f"{severity_badge(analyses[identifier])} · {short_time(latest_event_time(incident_by_id[identifier]))}"
                for identifier in shown_ids
            ],
            key="incident_picker",
            on_change=sync_incident_picker,
            label_visibility="collapsed",
        )
        st.caption(f"Showing {len(shown)} of {len(incidents)} incidents")
    return selected


def render_basic_info(incident: dict[str, Any]) -> None:
    latest = max(incident["events"], key=event_time)
    fields = (
        ("Account", code(incident["account"])),
        ("Department", md(incident["department"])),
        ("Known IPs", code(", ".join(incident.get("known_ips", [])) or "none listed")),
        ("Latest event", "Failed login" if latest["type"] == "login_failed" else "Successful login"),
        ("Timestamp (UTC)", md(latest["time_utc"])),
        ("Source IP · Location", f"{code(latest['ip'])} · {md(latest.get('country') or 'Unknown')}"),
    )
    with card(st, "inc-basic"):
        st.markdown("**Basic Information**")
        for row in (fields[:3], fields[3:]):
            for column, (label, value) in zip(st.columns(3, gap="small"), row):
                column.caption(label)
                column.markdown(value)


def render_timeline(incident: dict[str, Any], analysis: dict[str, Any]) -> None:
    evidence = set(analysis["evidence_ids"])
    known = set(incident.get("known_ips", []))
    ordered = sorted(incident["events"], key=event_time)
    with keyed(st, "layout-timeline"):
        events_column, engine_column = st.columns([3, 2], gap="medium")
    with events_column:
        st.caption("Chronological by time_utc. Tagged events are evidence cited by triggered rules.")
        timeline = keyed(st, "timeline")
        for event in reversed(ordered):
            failed = event["type"] == "login_failed"
            with keyed(timeline, f"tl-{slug(event['id'])}"):
                when, dot, what = st.columns([1.2, 0.3, 4.5], vertical_alignment="center")
                stamp = event_time(event)
                when.markdown(f"**{stamp:%H:%M}**  \n:gray[{stamp:%b %d}]")
                dot.markdown(f":{'red' if failed else 'green'}[:material/radio_button_checked:]")
                place = "known IP" if event["ip"] in known else "unfamiliar IP"
                tag = " :violet-background[evidence]" if event["id"] in evidence else ""
                what.markdown(
                    f"**{'Failed login' if failed else 'Successful login'}** from {code(event['ip'])} "
                    f"({place}, {md(event.get('country') or 'Unknown')}){tag}"
                )
        with st.expander("Event table"):
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
                    for event in ordered
                ],
                hide_index=True,
            )
    with card(engine_column, "inc-engine"):
        st.markdown("**Engine Analysis**")
        for flag in analysis["flags"] or ["No configured rule matched the available events."]:
            st.markdown(f"- {md(flag)}")
        st.caption(md(f"Suggested (simulated) action: {analysis['suggested_action']}"))
        st.caption("Rule-based findings and score: not a probability and not proof of compromise.")
        if st.button("View Full Report", key="engine_full_report", icon=":material/description:"):
            full_report_dialog(incident["id"])


@st.dialog("Engine analysis — full report", width="medium")
def full_report_dialog(incident_id: str) -> None:
    """Rule-by-rule breakdown from engine.py; no AI content is shown here."""
    incident, analysis = incident_by_id[incident_id], analyses[incident_id]
    st.markdown(
        f"{tone_icon(analysis)} **{md(incident_id)}** · {md(incident['title'])}  \n"
        f"Risk score **{analysis['risk_score']} / 100** · Severity {severity_badge(analysis)}"
    )
    with keyed(st, "report-scroll"):  # only the report body scrolls; summary and note stay put
        render_rules(incident, analysis, scope="dialog")
    st.caption(RISK_NOTE)


def render_rules(incident: dict[str, Any], analysis: dict[str, Any], scope: str = "tab") -> None:
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
    with keyed(st, f"layout-findings-{scope}"):  # the dialog renders a second copy
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
            st.markdown(report_markdown(st.session_state.report))
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
        st.info("Use **Request AI Report** above to generate a report. A Nebius API key is required.")
    else:
        st.info("No policy context matched, so an AI report cannot be requested for this incident.")


def render_policy_summary(matched_policies: list[dict[str, Any]]) -> None:
    with card(st, "inc-policies"):
        st.markdown("**Relevant Policies**")
        if not matched_policies:
            st.caption("No policy passage met the similarity threshold.")
        for index, policy in enumerate(matched_policies, 1):
            st.markdown(f"{index}\\. {md(policy['title'])}")
        st.caption("Full passages and similarity scores are in the Relevant Policies tab.")


def render_decision_panel(incident: dict[str, Any], analysis: dict[str, Any], context_id: str) -> bool:
    can_decide = can_record_decision(
        st.session_state.report,
        st.session_state.report_context_id,
        context_id,
        st.session_state.active_report_id,
        st.session_state.decision,
    )
    with card(st, "inc-decision"):
        st.markdown("**Take Action (Simulated)**")
        st.caption(f"SIMULATED ACTION — NO REAL ACCOUNT ACTION · Proposed: {md(analysis['suggested_action'])}")
        decision = st.session_state.decision
        earlier = next(
            (record for record in reversed(st.session_state.audit) if record["incident_id"] == incident["id"]), None
        )
        if decision:
            st.success(
                md(f"{decision['decision']} recorded at {decision['time_utc']} (UTC): {decision['outcome']}"),
                icon="📝",
            )
        else:
            if earlier:  # the active decision is cleared on leaving an incident; the audit keeps it
                st.info(
                    md(f"Last recorded decision: {earlier['decision']} at {earlier['time_utc']} (UTC). "
                       "A new decision needs a new citation-validated AI report."),
                    icon="📝",
                )
            if not st.session_state.report:
                st.caption("🔒 Locked until a citation-validated AI report is available for this incident.")
            elif not can_decide:
                st.caption("🔒 Locked: the AI report belongs to a different incident or context. Request a new report.")
        approve, reject = st.columns(2)
        for column, label, key, verdict, outcome in (
            (approve, "✓ Approve", "btn_approve", "APPROVED",
             f"Simulated response recorded for the proposed action: {analysis['suggested_action'].rstrip('.')}. "
             "No external system was changed."),
            (reject, "✕ Reject", "btn_reject", "REJECTED",
             "No action taken; recommendation rejected by demo analyst."),
        ):
            if column.button(label, key=key, disabled=not can_decide):
                if audit_decision(incident, verdict, outcome, context_id):
                    st.rerun()
                st.error("The decision was not recorded: the report is no longer valid for this context.")
        if (decision or earlier) and st.button("View in Audit History →", key="open_audit"):
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

    with card(st, "inc-header"):
        heading, action = st.columns([2.6, 1.4], vertical_alignment="center")
        with heading:
            st.markdown(f"### {tone_icon(analysis)} {md(incident['id'])}")
            st.markdown(f"{classification_badge(analysis)} {md(incident['title'])}")
        if action.button(
            "Request AI Report", key="ai_request_btn", icon=":material/auto_awesome:", disabled=not matched_policies
        ):
            run_ai_analysis(incident, analysis, matched_policies, context_id)
        classification = classification_of(analysis)
        st.caption(
            CLASSIFICATIONS[classification][1]
            if classification
            else "engine.py does not provide a classification yet. A low or zero score alone does not show "
            "that this activity is normal."
        )
        progress = st.empty()

    tone = incident_tone(analysis)
    severity_tone = SEVERITY_TONES.get(analysis.get("severity") or "", "violet")
    with keyed(st, "layout-inc-kpis"):
        cards = st.columns(3, gap="small")
    kpi_card(cards[0], "Risk score", f"{analysis['risk_score']} / 100", "Rule-based, not a probability", tone,
             "gpp_maybe", RISK_NOTE, compact=True)
    kpi_card(cards[1], "Severity", severity_text(analysis), "Derived by engine.py", severity_tone, "shield",
             compact=True)
    kpi_card(cards[2], "Priority", short_text(priority_text(analysis)),
             "Backend-provided" if analysis.get("investigation_priority") else "Not provided by the backend yet",
             "violet", "warning", compact=True)

    render_basic_info(incident)

    timeline_tab, rules_tab, policy_tab, ai_tab = st.tabs(
        ["Timeline", "Rules & Evidence", "Relevant Policies", "AI Analysis"]
    )
    with timeline_tab:
        render_timeline(incident, analysis)
    with rules_tab:
        render_rules(incident, analysis)
    with policy_tab:
        render_policies(matched_policies)
    with ai_tab:
        render_ai_panel(incident, analysis, matched_policies, context_id)

    with keyed(st, "layout-pair"):
        policies_column, decision_column = st.columns(2, gap="small")
    with policies_column:
        render_policy_summary(matched_policies)
    with decision_column:
        can_decide = render_decision_panel(incident, analysis, context_id)

    if st.session_state.report:
        ai_step = ":green[✔] AI report"
    elif st.session_state.report_status:
        ai_step = ":red[✖] AI report"
    else:
        ai_step = ":violet[●] AI report" if matched_policies else ":gray[○] AI report"
    if st.session_state.decision:
        decision_step = f":green[✔] Decision ({st.session_state.decision['decision'].title()})"
    else:
        decision_step = ":violet[●] Decision" if can_decide else ":gray[○] Decision"
    policy_step = ":green[✔] Policy" if matched_policies else ":red[✖] Policy"
    progress.caption(
        f":green[✔] Detect · :green[✔] Evidence ({len(analysis['evidence_ids'])}) · {policy_step} · "
        f"{ai_step} · {decision_step}"
    )


INCIDENT_FILTERS = {"All": None, "High severity": "HIGH", "Medium severity": "MEDIUM", "Low severity": "LOW"}
if any_classified:
    INCIDENT_FILTERS.update({key.replace("_", " ").title(): key for key in CLASSIFICATIONS})


def incidents_page() -> None:
    with keyed(st, "layout-toolbar"):
        heading, search, choose = st.columns([3, 2, 1], vertical_alignment="bottom")
    with heading:
        page_header("Security Incidents", "View and analyze individual incidents")
    search.text_input(
        "Search", placeholder="Search by incident ID, title, account…", key="incident_search",
        label_visibility="collapsed",
    )
    choose.selectbox(
        "Filter", list(INCIDENT_FILTERS), key="incident_filter", label_visibility="collapsed",
        format_func=lambda option: f"{option} ({sum(matches_filter(incident, option) for incident in incidents)})",
    )

    with keyed(st, "layout-incidents"):
        left, main = st.columns([1.25, 3], gap="medium")
    with left:
        selected = render_incident_list(filtered_incidents())
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
