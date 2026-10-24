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
st.set_page_config(
    page_title="GuardBee | Security Decision Copilot",
    page_icon=str(ROOT / "assets" / "favicon.png"),
    layout="wide",
)

# ---------------------------------------------------------------------------
# Classic SVG Icons
# ---------------------------------------------------------------------------
ICON_BEE = (
    '<svg class="gb-icon gb-icon-bee" width="20" height="20" viewBox="0 0 24 24" fill="none" '
    'stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">'
    '<path d="M12 2L4.5 5.5v5.5c0 4.8 3.2 9.3 7.5 10.5 4.3-1.2 7.5-5.7 7.5-10.5V5.5L12 2z"/>'
    '<path d="M9 10.5h6"/><path d="M9 13.5h6"/><circle cx="12" cy="7.5" r="1.2" fill="currentColor"/>'
    '</svg>'
)

ICON_LOCK = (
    '<svg class="gb-icon" width="14" height="14" viewBox="0 0 24 24" fill="none" '
    'stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
    '<rect x="3" y="11" width="18" height="11" rx="2" ry="2"/>'
    '<path d="M7 11V7a5 5 0 0 1 10 0v4"/>'
    '</svg>'
)

ICON_CHECK = (
    '<svg class="gb-icon" width="13" height="13" viewBox="0 0 24 24" fill="none" '
    'stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round">'
    '<polyline points="20 6 9 17 4 12"/>'
    '</svg>'
)

ICON_CROSS = (
    '<svg class="gb-icon" width="13" height="13" viewBox="0 0 24 24" fill="none" '
    'stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round">'
    '<line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>'
    '</svg>'
)

ICON_FLAG = (
    '<svg class="gb-icon" width="12" height="12" viewBox="0 0 24 24" fill="none" '
    'stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
    '<path d="M4 15s1-1 4-1 5 2 8 2 4-1 4-1V3s-1 1-4 1-5-2-8-2-4 1-4 1z"/>'
    '<line x1="4" y1="22" x2="4" y2="15"/>'
    '</svg>'
)

ICON_ALERT_CIRCLE = (
    '<svg class="gb-icon" width="13" height="13" viewBox="0 0 24 24" fill="none" '
    'stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">'
    '<circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/>'
    '</svg>'
)

ICON_ALERT_TRIANGLE = (
    '<svg class="gb-icon" width="13" height="13" viewBox="0 0 24 24" fill="none" '
    'stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">'
    '<path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/>'
    '<line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/>'
    '</svg>'
)

ICON_INFO = (
    '<svg class="gb-icon" width="14" height="14" viewBox="0 0 24 24" fill="none" '
    'stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
    '<circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/>'
    '</svg>'
)

ICON_SPARKLE = (
    '<svg class="gb-icon" width="14" height="14" viewBox="0 0 24 24" fill="none" '
    'stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">'
    '<path d="m12 3-1.9 5.8a2 2 0 0 1-1.3 1.3L3 12l5.8 1.9a2 2 0 0 1 1.3 1.3L12 21l1.9-5.8a2 2 0 0 1 1.3-1.3L21 12l-5.8-1.9a2 2 0 0 1-1.3-1.3L12 3z"/>'
    '</svg>'
)

ICON_POLICY = (
    '<svg class="gb-icon" width="14" height="14" viewBox="0 0 24 24" fill="none" '
    'stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">'
    '<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/>'
    '</svg>'
)

ICON_SCALE = (
    '<svg class="gb-icon" width="15" height="15" viewBox="0 0 24 24" fill="none" '
    'stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">'
    '<path d="m16 16 3-8 3 8c-.87.65-1.92 1-3 1s-2.13-.35-3-1Z"/><path d="m2 16 3-8 3 8c-.87.65-1.92 1-3 1s-2.13-.35-3-1Z"/><path d="M7 21h10"/><path d="M12 3v18"/><path d="M3 7h2c2 0 5-1 7-2 2 1 5 2 7 2h2"/>'
    '</svg>'
)

ICON_AUDIT = (
    '<svg class="gb-icon" width="14" height="14" viewBox="0 0 24 24" fill="none" '
    'stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">'
    '<path d="M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2"/><rect x="8" y="2" width="8" height="4" rx="1" ry="1"/><path d="M9 12h6"/><path d="M9 16h6"/>'
    '</svg>'
)

# ---------------------------------------------------------------------------
# Custom CSS — injected once at startup
# ---------------------------------------------------------------------------
st.markdown(
    """
<style>
/* ── Google Fonts ─────────────────────────────────────────────────── */
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');

html, body, [class*="css"], .stApp {
    font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif;
    background-color: #FEFAF3 !important;
    color: #22332B;
}

/* ── Global page tweaks ───────────────────────────────────────────── */
.main .block-container {
    padding-top: 1.3rem;
    padding-bottom: 2.5rem;
    max-width: 1200px;
}

/* ── Classic SVG Icon styling ─────────────────────────────────────── */
.gb-icon {
    display: inline-block;
    vertical-align: middle;
    margin-right: 0.35rem;
    flex-shrink: 0;
}
.gb-header-brand-icon {
    width: 44px;
    height: 44px;
    border-radius: 8px;
    background: #84A282;
    color: #FEFAF3;
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
}
.gb-header-brand-icon .gb-icon {
    margin-right: 0;
}

/* ── Header banner ────────────────────────────────────────────────── */
.gb-header {
    background: #FFFFFF;
    border: 1px solid #B8CFB3;
    border-top: 3px solid #84A282;
    border-radius: 8px;
    padding: 1.2rem 1.6rem;
    margin-bottom: 0.85rem;
    display: flex;
    align-items: center;
    gap: 1.1rem;
}
.gb-header-title {
    font-size: 1.45rem;
    font-weight: 700;
    color: #1E2E25;
    letter-spacing: -0.01em;
    margin: 0;
    line-height: 1.25;
    display: flex;
    align-items: center;
    gap: 0.5rem;
}
.gb-header-sub {
    font-size: 0.82rem;
    color: #5D7267;
    margin-top: 0.2rem;
}
.gb-safety-banner {
    background: #FFFFFF;
    border: 1px solid #B8CFB3;
    border-left: 3px solid #84A282;
    border-radius: 6px;
    padding: 0.7rem 1.1rem;
    font-size: 0.82rem;
    color: #4A5D53;
    margin-bottom: 1.2rem;
    display: flex;
    align-items: flex-start;
    gap: 0.65rem;
    line-height: 1.45;
}
.gb-safety-banner .gb-icon {
    color: #84A282;
    margin-top: 0.15rem;
}

/* ── Severity badges ──────────────────────────────────────────────── */
.sev-badge {
    display: inline-flex;
    align-items: center;
    gap: 0.4rem;
    padding: 0.28rem 0.8rem;
    border-radius: 6px;
    font-weight: 600;
    font-size: 0.78rem;
    letter-spacing: 0.04em;
    text-transform: uppercase;
}
.sev-high {
    background: #F6E2E9;
    color: #8B2841;
    border: 1px solid #E5B8C7;
}
.sev-medium {
    background: #FEFAF3;
    color: #8B651B;
    border: 1px solid #D8BC79;
}
.sev-low {
    background: #EAF2E8;
    color: #2F522E;
    border: 1px solid #B8CFB3;
}

/* ── Metric cards ─────────────────────────────────────────────────── */
.gb-metric-row {
    display: flex;
    gap: 0.75rem;
    margin-bottom: 1rem;
}
.gb-metric-card {
    background: #FFFFFF;
    border: 1px solid #DCE6DA;
    border-radius: 8px;
    padding: 1.1rem 1.2rem;
    text-align: center;
}
.gb-metric-label {
    font-size: 0.72rem;
    color: #647A6F;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    font-weight: 600;
    margin-bottom: 0.4rem;
}
.gb-metric-value {
    font-size: 1.65rem;
    font-weight: 700;
    color: #1E2E25;
    line-height: 1.15;
}
.gb-metric-value-accent, .gb-metric-value-gold {
    color: #84A282;
}

/* ── Section headers ──────────────────────────────────────────────── */
.gb-section-header {
    font-size: 0.74rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.09em;
    color: #5D7267;
    padding: 0.5rem 0 0.35rem;
    border-bottom: 1px solid #DCE6DA;
    margin-bottom: 0.85rem;
    display: flex;
    align-items: center;
}

/* ── Info card (incident context) ─────────────────────────────────── */
.gb-info-card {
    background: #FFFFFF;
    border: 1px solid #DCE6DA;
    border-radius: 8px;
    padding: 1rem 1.25rem;
    margin-bottom: 0.85rem;
    font-size: 0.88rem;
}
.gb-info-card .label {
    color: #647A6F;
    font-size: 0.72rem;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    margin-bottom: 0.2rem;
    font-weight: 600;
}
.gb-info-card .value {
    color: #1E2E25;
    font-weight: 500;
}
.gb-info-card code {
    background: #FEFAF3;
    color: #2F522E;
    border: 1px solid #B8CFB3;
    padding: 0.15rem 0.45rem;
    border-radius: 4px;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.8rem;
}
.gb-dept-sensitive {
    display: inline-flex;
    align-items: center;
    gap: 0.3rem;
    background: #F6E2E9;
    color: #8B2841;
    border: 1px solid #E5B8C7;
    padding: 0.15rem 0.55rem;
    border-radius: 4px;
    font-weight: 600;
    font-size: 0.8rem;
}

/* ── Timeline table ───────────────────────────────────────────────── */
.gb-timeline {
    background: #FFFFFF;
    border: 1px solid #DCE6DA;
    border-radius: 8px;
    overflow: hidden;
    margin-bottom: 0.85rem;
}
.gb-timeline-header {
    display: grid;
    grid-template-columns: 90px 160px 140px 140px 100px;
    background: #F4EFE6;
    padding: 0.55rem 1rem;
    font-size: 0.72rem;
    font-weight: 700;
    color: #5D7267;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    gap: 0.5rem;
}
.gb-timeline-row {
    display: grid;
    grid-template-columns: 90px 160px 140px 140px 100px;
    padding: 0.6rem 1rem;
    font-size: 0.84rem;
    gap: 0.5rem;
    border-top: 1px solid #EEF3EC;
    align-items: center;
}
.gb-timeline-row:hover {
    background: #FBFDF9;
}
.gb-evt-id {
    font-family: 'JetBrains Mono', monospace;
    color: #496947;
    font-size: 0.78rem;
    font-weight: 500;
}
.gb-evt-time {
    color: #5D7267;
    font-size: 0.78rem;
    font-family: 'JetBrains Mono', monospace;
}
.gb-evt-fail {
    color: #8B2841;
    font-weight: 600;
    display: inline-flex;
    align-items: center;
    gap: 0.3rem;
}
.gb-evt-success {
    color: #2F522E;
    font-weight: 600;
    display: inline-flex;
    align-items: center;
    gap: 0.3rem;
}
.gb-evt-ip {
    font-family: 'JetBrains Mono', monospace;
    color: #22332B;
    font-size: 0.78rem;
}
.gb-evt-ip-unfamiliar {
    color: #8B651B;
    font-weight: 600;
    display: inline-flex;
    align-items: center;
    gap: 0.3rem;
}
.gb-evt-country {
    color: #5D7267;
    font-size: 0.8rem;
}

/* ── Rule hit cards ───────────────────────────────────────────────── */
.gb-rule-card {
    background: #FFFFFF;
    border: 1px solid #DCE6DA;
    border-left: 3px solid #84A282;
    border-radius: 0 8px 8px 0;
    padding: 0.85rem 1.15rem;
    margin-bottom: 0.65rem;
}
.gb-rule-id {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.72rem;
    color: #84A282;
    font-weight: 600;
    margin-bottom: 0.2rem;
}
.gb-rule-flag {
    font-size: 0.92rem;
    color: #1E2E25;
    font-weight: 600;
    margin-bottom: 0.35rem;
}
.gb-rule-pts {
    font-size: 0.76rem;
    color: #647A6F;
}
.gb-rule-evids {
    margin-top: 0.45rem;
    display: flex;
    flex-wrap: wrap;
    gap: 0.35rem;
}
.gb-evid-tag {
    background: #FEFAF3;
    color: #355633;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.72rem;
    padding: 0.15rem 0.5rem;
    border-radius: 4px;
    border: 1px solid #B8CFB3;
}
.gb-no-rules {
    background: #EAF2E8;
    border: 1px solid #B8CFB3;
    border-radius: 6px;
    padding: 0.85rem 1.15rem;
    color: #2F522E;
    font-size: 0.88rem;
    display: flex;
    align-items: center;
    gap: 0.45rem;
}

/* ── AI analysis section ──────────────────────────────────────────── */
.gb-ai-divider {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    margin: 1.4rem 0 0.85rem;
    color: #5D7267;
    font-size: 0.74rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.08em;
}
.gb-ai-divider::before, .gb-ai-divider::after {
    content: '';
    flex: 1;
    height: 1px;
    background: #DCE6DA;
}
.gb-ai-label {
    background: #FFFFFF;
    border: 1px solid #B8CFB3;
    border-radius: 4px;
    padding: 0.2rem 0.65rem;
    white-space: nowrap;
    display: flex;
    align-items: center;
    gap: 0.35rem;
}
.gb-model-info {
    background: #FFFFFF;
    border: 1px solid #DCE6DA;
    border-radius: 6px;
    padding: 0.55rem 0.95rem;
    font-size: 0.78rem;
    color: #5D7267;
    margin-bottom: 0.85rem;
    font-family: 'JetBrains Mono', monospace;
}
.gb-report-container {
    background: #FFFFFF;
    border: 1px solid #DCE6DA;
    border-radius: 8px;
    padding: 1.2rem 1.4rem;
    margin-top: 0.85rem;
    color: #1E2E25;
    line-height: 1.6;
}
.gb-state-info {
    background: #FEFAF3;
    border: 1px solid #B8CFB3;
    border-radius: 6px;
    padding: 0.85rem 1.1rem;
    color: #4A5D53;
    font-size: 0.85rem;
    margin-top: 0.65rem;
    display: flex;
    align-items: flex-start;
    gap: 0.5rem;
}
.gb-state-error {
    background: #F6E2E9;
    border: 1px solid #E5B8C7;
    border-radius: 6px;
    padding: 0.85rem 1.1rem;
    color: #8B2841;
    font-size: 0.85rem;
    margin-top: 0.65rem;
}
.gb-state-success {
    background: #EAF2E8;
    border: 1px solid #B8CFB3;
    border-radius: 6px;
    padding: 0.65rem 1rem;
    color: #2F522E;
    font-size: 0.84rem;
    margin-bottom: 0.65rem;
    display: flex;
    align-items: center;
    gap: 0.45rem;
}
.gb-no-policy-warn {
    background: #FEFAF3;
    border: 1px solid #D8BC79;
    border-left: 3px solid #8B651B;
    border-radius: 6px;
    padding: 0.85rem 1.1rem;
    color: #8B651B;
    font-size: 0.85rem;
    margin-bottom: 0.85rem;
    display: flex;
    align-items: flex-start;
    gap: 0.5rem;
}

/* ── Policy cards ─────────────────────────────────────────────────── */
.gb-policy-card {
    background: #FFFFFF;
    border: 1px solid #DCE6DA;
    border-left: 3px solid #84A282;
    border-radius: 0 8px 8px 0;
    padding: 0.95rem 1.2rem;
    margin-bottom: 0.85rem;
}
.gb-policy-id {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.72rem;
    color: #84A282;
    font-weight: 600;
    margin-bottom: 0.2rem;
}
.gb-policy-title {
    font-size: 0.94rem;
    color: #1E2E25;
    font-weight: 600;
    margin-bottom: 0.55rem;
}
.gb-policy-sim-bar-wrap {
    display: flex;
    align-items: center;
    gap: 0.65rem;
    margin-bottom: 0.65rem;
}
.gb-policy-sim-label {
    font-size: 0.72rem;
    color: #647A6F;
}
.gb-policy-sim-bar {
    flex: 1;
    height: 6px;
    background: #F4EFE6;
    border-radius: 3px;
    overflow: hidden;
}
.gb-policy-sim-fill {
    height: 100%;
    background: #84A282;
    border-radius: 3px;
}
.gb-policy-sim-pct {
    font-size: 0.74rem;
    color: #84A282;
    font-weight: 600;
    min-width: 42px;
    text-align: right;
    font-family: 'JetBrains Mono', monospace;
}
.gb-policy-text {
    font-size: 0.85rem;
    color: #4A5D53;
    line-height: 1.6;
}
.gb-policy-note {
    background: #FFFFFF;
    border: 1px solid #B8CFB3;
    border-radius: 6px;
    padding: 0.7rem 1rem;
    font-size: 0.82rem;
    color: #4A5D53;
    margin-bottom: 0.85rem;
    display: flex;
    align-items: flex-start;
    gap: 0.55rem;
}

/* ── Decision tab ─────────────────────────────────────────────────── */
.gb-decision-action {
    background: #FFFFFF;
    border: 1px solid #DCE6DA;
    border-left: 3px solid #84A282;
    border-radius: 0 8px 8px 0;
    padding: 1.05rem 1.25rem;
    margin-bottom: 0.85rem;
}
.gb-decision-action .label {
    font-size: 0.72rem;
    color: #647A6F;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    margin-bottom: 0.35rem;
    font-weight: 600;
}
.gb-decision-action .value {
    font-size: 0.94rem;
    color: #1E2E25;
    font-weight: 600;
}
.gb-sim-disclaimer {
    font-size: 0.78rem;
    color: #5D7267;
    padding: 0.4rem 0;
    margin-bottom: 0.85rem;
    display: flex;
    align-items: center;
    gap: 0.45rem;
}
.gb-gate-state {
    border-radius: 6px;
    padding: 0.8rem 1.1rem;
    font-size: 0.85rem;
    margin-bottom: 0.85rem;
    display: flex;
    align-items: flex-start;
    gap: 0.5rem;
}
.gb-gate-locked {
    background: #F6E2E9;
    border: 1px solid #E5B8C7;
    color: #8B2841;
}
.gb-gate-used {
    background: #FEFAF3;
    border: 1px solid #B8CFB3;
    color: #4A5D53;
}
.gb-decision-result {
    background: #EAF2E8;
    border: 1px solid #B8CFB3;
    border-radius: 6px;
    padding: 0.85rem 1.15rem;
    margin: 0.85rem 0;
}
.gb-decision-result .result-label {
    font-size: 0.72rem;
    color: #5D7267;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    margin-bottom: 0.25rem;
    font-weight: 600;
}
.gb-decision-result .result-approved {
    color: #2F522E;
    font-weight: 600;
    font-size: 0.92rem;
    display: flex;
    align-items: center;
    gap: 0.4rem;
}
.gb-decision-result .result-rejected {
    color: #8B2841;
    font-weight: 600;
    font-size: 0.92rem;
    display: flex;
    align-items: center;
    gap: 0.4rem;
}
.gb-audit-header {
    font-size: 0.74rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.09em;
    color: #5D7267;
    padding-bottom: 0.35rem;
    border-bottom: 1px solid #DCE6DA;
    margin-bottom: 0.65rem;
    display: flex;
    align-items: center;
    gap: 0.45rem;
}
.gb-audit-empty {
    background: #FFFFFF;
    border: 1px solid #DCE6DA;
    border-radius: 6px;
    padding: 1.4rem;
    text-align: center;
    color: #647A6F;
    font-size: 0.85rem;
}
.gb-audit-session-note {
    font-size: 0.75rem;
    color: #647A6F;
    margin-top: 0.5rem;
    display: flex;
    align-items: center;
    gap: 0.35rem;
}

/* ── Sidebar ──────────────────────────────────────────────────────── */
section[data-testid="stSidebar"] {
    background: #F4EFE6 !important;
    border-right: 1px solid #DCE6DA;
}
section[data-testid="stSidebar"] .block-container {
    padding-top: 1.5rem;
}
.gb-sidebar-brand {
    font-size: 1.2rem;
    font-weight: 700;
    color: #1E2E25;
    display: flex;
    align-items: center;
    gap: 0.5rem;
    padding-bottom: 0.85rem;
    border-bottom: 1px solid #DCE6DA;
    margin-bottom: 0.85rem;
    letter-spacing: -0.01em;
}
.gb-sidebar-brand .gb-icon {
    color: #84A282;
}
.gb-sidebar-section {
    font-size: 0.68rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    color: #647A6F;
    margin: 1rem 0 0.45rem;
}
.gb-sidebar-step {
    display: flex;
    gap: 0.65rem;
    align-items: flex-start;
    padding: 0.4rem 0;
    font-size: 0.8rem;
    color: #22332B;
    line-height: 1.4;
}
.gb-sidebar-step-num {
    background: #FEFAF3;
    color: #84A282;
    border: 1px solid #B8CFB3;
    font-size: 0.65rem;
    font-weight: 700;
    width: 20px;
    height: 20px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
    margin-top: 0.05rem;
}
.gb-sidebar-incident-card {
    background: #FFFFFF;
    border: 1px solid #DCE6DA;
    border-radius: 6px;
    padding: 0.75rem 0.95rem;
    margin-top: 0.55rem;
    font-size: 0.8rem;
}
.gb-sidebar-incident-id {
    color: #84A282;
    font-family: 'JetBrains Mono', monospace;
    font-weight: 600;
    font-size: 0.78rem;
}
.gb-sidebar-incident-title {
    color: #1E2E25;
    font-weight: 600;
    margin-top: 0.25rem;
}
.gb-sidebar-risk {
    display: flex;
    gap: 0.55rem;
    align-items: center;
    margin-top: 0.55rem;
}
.gb-sidebar-score {
    font-size: 1.1rem;
    font-weight: 700;
    color: #84A282;
}

/* ── Tab styling ──────────────────────────────────────────────────── */
.stTabs [data-baseweb="tab-list"] {
    gap: 0;
    background: #F4EFE6;
    border-radius: 8px 8px 0 0;
    padding: 0.35rem 0.35rem 0;
    border: 1px solid #DCE6DA;
    border-bottom: none;
}
.stTabs [data-baseweb="tab"] {
    border-radius: 6px 6px 0 0 !important;
    padding: 0.55rem 1.3rem !important;
    font-size: 0.84rem !important;
    font-weight: 600 !important;
    color: #5D7267 !important;
    background: transparent !important;
    border: none !important;
}
.stTabs [aria-selected="true"] {
    background: #FFFFFF !important;
    color: #1E2E25 !important;
    border-bottom: 2px solid #84A282 !important;
}
.stTabs [data-baseweb="tab-panel"] {
    background: #FFFFFF;
    border: 1px solid #DCE6DA;
    border-top: none;
    border-radius: 0 0 8px 8px;
    padding: 1.35rem 1.6rem;
}

/* ── Streamlit Button Customization ───────────────────────────────── */
button[kind="primary"] {
    background-color: #84A282 !important;
    color: #FFFFFF !important;
    border: 1px solid #708D6E !important;
    border-radius: 6px !important;
    font-weight: 600 !important;
    transition: background-color 0.15s ease !important;
}
button[kind="primary"]:hover {
    background-color: #729070 !important;
    border-color: #5E7A5C !important;
}
button[kind="secondary"] {
    background-color: #FFFFFF !important;
    color: #22332B !important;
    border: 1px solid #B8CFB3 !important;
    border-radius: 6px !important;
    font-weight: 500 !important;
    transition: background-color 0.15s ease, border-color 0.15s ease !important;
}
button[kind="secondary"]:hover {
    background-color: #F4EFE6 !important;
    border-color: #84A282 !important;
}
</style>
""",
    unsafe_allow_html=True,
)


# ---------------------------------------------------------------------------
# Helper: severity badge HTML
# ---------------------------------------------------------------------------
def severity_badge(severity: str) -> str:
    icons = {
        "HIGH": ICON_ALERT_CIRCLE,
        "MEDIUM": ICON_ALERT_TRIANGLE,
        "LOW": ICON_CHECK,
    }
    classes = {"HIGH": "sev-high", "MEDIUM": "sev-medium", "LOW": "sev-low"}
    icon = icons.get(severity, ICON_INFO)
    css_class = classes.get(severity, "sev-low")
    return f'<span class="sev-badge {css_class}">{icon} <span>{severity} RISK</span></span>'


# ---------------------------------------------------------------------------
# Helper: render event timeline rows
# ---------------------------------------------------------------------------
def render_timeline(incident: dict[str, Any]) -> None:
    known_ips = set(incident.get("known_ips", []))
    events = sorted(incident["events"], key=lambda e: e["time_utc"])
    rows_html = ""
    for evt in events:
        is_fail = evt["type"] == "login_failed"
        is_unfamiliar = evt["ip"] not in known_ips
        type_class = "gb-evt-fail" if is_fail else "gb-evt-success"
        type_icon = ICON_CROSS if is_fail else ICON_CHECK
        type_label = f'<span class="{type_class}">{type_icon} {evt["type"]}</span>'
        ip_class = "gb-evt-ip gb-evt-ip-unfamiliar" if is_unfamiliar else "gb-evt-ip"
        ip_label = evt["ip"] + (f" {ICON_FLAG}" if is_unfamiliar else "")
        # Format timestamp for readability
        ts = evt["time_utc"].replace("T", " ").replace("Z", " UTC")
        rows_html += f"""
        <div class="gb-timeline-row">
            <span class="gb-evt-id">{evt['id']}</span>
            <span class="gb-evt-time">{ts}</span>
            <span>{type_label}</span>
            <span class="{ip_class}">{ip_label}</span>
            <span class="gb-evt-country">{evt['country']}</span>
        </div>"""
    st.markdown(
        f"""
        <div class="gb-timeline">
            <div class="gb-timeline-header">
                <span>Event ID</span>
                <span>Time (UTC)</span>
                <span>Type</span>
                <span>IP Address</span>
                <span>Country</span>
            </div>
            {rows_html}
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown(
        f"<span style='font-size:0.75rem;color:#5D7267;'>{ICON_FLAG} Unfamiliar IP (not in known IPs: {', '.join(sorted(known_ips))})</span>",
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# Helper: render rule hit cards
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
            f'<span class="gb-evid-tag">{eid}</span>'
            for eid in hit.get("evidence_ids", [])
        ) or "<span style='color:#647A6F;font-size:0.78rem;'>No linked event IDs</span>"
        st.markdown(
            f"""
            <div class="gb-rule-card">
                <div class="gb-rule-id">{hit['rule_id']}</div>
                <div class="gb-rule-flag">{hit['flag']}</div>
                <div class="gb-rule-pts">+{hit['points']} risk points</div>
                <div class="gb-rule-evids">{evids_html}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )


# ---------------------------------------------------------------------------
# Helper: render policy cards
# ---------------------------------------------------------------------------
def render_policy_cards(matched_policies: list[dict[str, Any]]) -> None:
    for policy in matched_policies:
        score = policy["match_score"]
        bar_pct = min(int(score * 100 / 0.5 * 100), 100)  # scale bar to 50% = full
        st.markdown(
            f"""
            <div class="gb-policy-card">
                <div class="gb-policy-id">{policy['id']}</div>
                <div class="gb-policy-title">{policy['title']}</div>
                <div class="gb-policy-sim-bar-wrap">
                    <span class="gb-policy-sim-label">TF-IDF similarity</span>
                    <div class="gb-policy-sim-bar">
                        <div class="gb-policy-sim-fill" style="width:{bar_pct}%;"></div>
                    </div>
                    <span class="gb-policy-sim-pct">{score:.3f}</span>
                </div>
                <div class="gb-policy-text">{policy['text']}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )


# ---------------------------------------------------------------------------
# Session helpers — unchanged logic
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


# ---------------------------------------------------------------------------
# Boot
# ---------------------------------------------------------------------------
initialize_session()

# Load data — safe error state
try:
    incidents = load_incidents(ROOT / "data" / "incidents.json")
    policies = load_policies(ROOT / "data" / "policies.json")
except DataValidationError as exc:
    st.markdown(
        f'<div class="gb-header"><span class="gb-header-title">{ICON_BEE} GuardBee</span></div>',
        unsafe_allow_html=True,
    )
    st.error("GuardBee could not load its synthetic data safely.")
    st.markdown(
        f'<div class="gb-state-error">{ICON_ALERT_CIRCLE} The data file has a validation problem. Correct the file and reload the app to continue.</div>',
        unsafe_allow_html=True,
    )
    st.stop()

incident_by_id = {incident["id"]: incident for incident in incidents}

# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------
with st.sidebar:
    st.markdown(
        f'<div class="gb-sidebar-brand">{ICON_BEE} GuardBee</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div class="gb-sidebar-section">Select Incident</div>',
        unsafe_allow_html=True,
    )
    selected_id = st.selectbox(
        "Incident",
        options=list(incident_by_id),
        format_func=lambda identifier: f"{identifier} — {incident_by_id[identifier]['title']}",
        label_visibility="collapsed",
    )
    incident = incident_by_id[selected_id]
    reset_investigation_state(selected_id)

    # Run analysis for sidebar summary
    analysis = analyze_incident(incident)
    query = " ".join(
        [incident["title"], incident["department"], *analysis["flags"], analysis["suggested_action"]]
    )
    matched_policies = retrieve_policies(query, policies)
    current_context_id = analysis_context_id(incident, analysis, matched_policies)

    sev = analysis["severity"]
    st.markdown(
        f"""
        <div class="gb-sidebar-incident-card">
            <div class="gb-sidebar-incident-id">{incident['id']}</div>
            <div class="gb-sidebar-incident-title">{incident['title']}</div>
            <div class="gb-sidebar-risk">
                <span class="gb-sidebar-score">{analysis['risk_score']}/100</span>
                {severity_badge(sev)}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        '<div class="gb-sidebar-section">Investigation Steps</div>',
        unsafe_allow_html=True,
    )
    steps = [
        ("Investigate", "Review event timeline and deterministic rule evidence"),
        ("Policy retrieval", "Check matched company policy passages"),
        ("AI Analysis", "Request a live Nemotron report (requires API key)"),
        ("Decision & audit", "Approve or Reject after a valid AI report"),
    ]
    for i, (step, desc) in enumerate(steps, 1):
        st.markdown(
            f'<div class="gb-sidebar-step"><div class="gb-sidebar-step-num">{i}</div><div>{step} — <span style="color:#5D7267">{desc}</span></div></div>',
            unsafe_allow_html=True,
        )

    st.markdown(
        '<div class="gb-sidebar-section">About</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div style="font-size:0.77rem;color:#5D7267;line-height:1.6;">Synthetic incidents only. Deterministic Python rules, not AI, compute the risk score. No real account, session, or password is changed.</div>',
        unsafe_allow_html=True,
    )

# ---------------------------------------------------------------------------
# Main — Page header
# ---------------------------------------------------------------------------
st.markdown(
    f"""
    <div class="gb-header">
        <div class="gb-header-brand-icon">{ICON_BEE}</div>
        <div>
            <div class="gb-header-title">GuardBee &mdash; Security Decision Copilot</div>
            <div class="gb-header-sub">Synthetic login incidents only &nbsp;&bull;&nbsp; Deterministic detection &nbsp;&bull;&nbsp; Human-approved simulation</div>
        </div>
    </div>
    <div class="gb-safety-banner">
        {ICON_LOCK}
        <div><strong>Demo safety:</strong> GuardBee never changes real accounts, sessions, or systems. All incidents, accounts, and IP addresses are synthetic. Audit history is temporary to this browser session only.</div>
    </div>
    """,
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# Risk summary metrics
# ---------------------------------------------------------------------------
sev = analysis["severity"]
c1, c2, c3, c4 = st.columns(4)
with c1:
    st.markdown(
        f"""<div class="gb-metric-card">
            <div class="gb-metric-label">Synthetic Incidents</div>
            <div class="gb-metric-value gb-metric-value-accent">{len(incidents)}</div>
        </div>""",
        unsafe_allow_html=True,
    )
with c2:
    st.markdown(
        f"""<div class="gb-metric-card">
            <div class="gb-metric-label">Deterministic Risk Score</div>
            <div class="gb-metric-value gb-metric-value-accent">{analysis['risk_score']}<span style="font-size:1rem;color:#647A6F;">/100</span></div>
        </div>""",
        unsafe_allow_html=True,
    )
with c3:
    st.markdown(
        f"""<div class="gb-metric-card">
            <div class="gb-metric-label">Severity</div>
            <div style="margin-top:0.35rem">{severity_badge(sev)}</div>
        </div>""",
        unsafe_allow_html=True,
    )
with c4:
    st.markdown(
        f"""<div class="gb-metric-card">
            <div class="gb-metric-label">Evidence Events</div>
            <div class="gb-metric-value">{len(analysis['evidence_ids'])}</div>
        </div>""",
        unsafe_allow_html=True,
    )

st.markdown("<div style='height:0.75rem'></div>", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Tabs
# ---------------------------------------------------------------------------
investigate_tab, policy_tab, decision_tab = st.tabs(
    ["Investigate", "Policy Retrieval", "Decision & Audit"]
)

# ── Investigate Tab ─────────────────────────────────────────────────────────
with investigate_tab:
    # Incident context card
    dept = incident["department"]
    dept_label = (
        f'<span class="gb-dept-sensitive">{ICON_ALERT_TRIANGLE} {dept} (Sensitive)</span>'
        if dept == "Finance"
        else f'<span class="value">{dept}</span>'
    )
    st.markdown(
        f"""
        <div class="gb-info-card">
            <div style="display:flex; gap:2rem; flex-wrap:wrap;">
                <div><div class="label">Incident ID</div><code>{incident['id']}</code></div>
                <div><div class="label">Title</div><span class="value">{incident['title']}</span></div>
                <div><div class="label">Synthetic Account</div><code>{incident['account']}</code></div>
                <div><div class="label">Department</div>{dept_label}</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Event timeline
    st.markdown('<div class="gb-section-header">Event Timeline</div>', unsafe_allow_html=True)
    render_timeline(incident)

    # Deterministic rule evidence
    st.markdown(
        '<div class="gb-section-header">Deterministic Rule Evidence</div>',
        unsafe_allow_html=True,
    )
    render_rule_hits(analysis)
    if analysis["evidence_ids"]:
        evids_str = " &nbsp;·&nbsp; ".join(
            f'<span class="gb-evid-tag">{eid}</span>' for eid in analysis["evidence_ids"]
        )
        st.markdown(
            f'<div style="font-size:0.78rem;color:#5D7267;margin-top:-0.3rem;margin-bottom:0.5rem;">All evidence IDs: {evids_str}</div>',
            unsafe_allow_html=True,
        )

    # Suggested action
    st.markdown(
        f"""
        <div class="gb-info-card" style="border-left:3px solid #84A282;border-radius:0 8px 8px 0;padding-left:1rem;">
            <div class="label">Suggested Action</div>
            <div class="value" style="margin-top:0.25rem;">{analysis['suggested_action']}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # AI analysis section
    st.markdown(
        f'<div class="gb-ai-divider"><span class="gb-ai-label">{ICON_SPARKLE} AI-Generated Analysis (Optional)</span></div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        f'<div class="gb-model-info">Nebius Token Factory &nbsp;·&nbsp; Model: {read_model()}</div>',
        unsafe_allow_html=True,
    )

    if not matched_policies:
        st.markdown(
            f'<div class="gb-no-policy-warn">{ICON_ALERT_CIRCLE} No policy passage met the similarity threshold. AI analysis and approval remain unavailable &mdash; there is no valid policy context to cite.</div>',
            unsafe_allow_html=True,
        )

    if st.button(
        "Analyze with AI  →",
        type="primary",
        disabled=not bool(matched_policies),
        use_container_width=True,
    ):
        clear_report_state()
        try:
            with st.spinner("Calling Nebius Token Factory. GuardBee does not fabricate AI reports..."):
                report = generate_report(
                    read_api_key(), incident, analysis, matched_policies, model=read_model()
                )
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
            # Display a safe, concise message — never expose raw provider details or keys
            safe_msg = str(exc)
            st.session_state.report_status = safe_msg

    if st.session_state.report:
        st.markdown(
            f'<div class="gb-state-success">{ICON_CHECK} {st.session_state.report_status}</div>',
            unsafe_allow_html=True,
        )
        st.markdown(
            '<div class="gb-report-container">', unsafe_allow_html=True
        )
        st.markdown(st.session_state.report)
        st.markdown("</div>", unsafe_allow_html=True)
    elif st.session_state.report_status:
        st.markdown(
            f'<div class="gb-state-error">{ICON_ALERT_CIRCLE} AI report unavailable &mdash; {st.session_state.report_status}<br><span style="font-size:0.8rem;opacity:0.85;">Approval remains disabled. Verify the API key, network access, account credits, and configured model name.</span></div>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            f'<div class="gb-state-info">{ICON_INFO} Configure a Nebius API key in <code>.streamlit/secrets.toml</code> and click <strong>Analyze with AI</strong> to unlock the human decision controls.</div>',
            unsafe_allow_html=True,
        )

# ── Policy Retrieval Tab ─────────────────────────────────────────────────────
with policy_tab:
    st.markdown(
        f"""
        <div class="gb-policy-note">
            {ICON_POLICY} Retrieved locally using scikit-learn TF-IDF cosine similarity.
            Only passages scoring at least <strong>{DEFAULT_MIN_SIMILARITY:.2f}</strong> are shown.
            These are reference policies for the analyst &mdash; they are not instructions for the AI.
        </div>
        """,
        unsafe_allow_html=True,
    )
    if not matched_policies:
        st.markdown(
            f'<div class="gb-state-info">{ICON_INFO} No sample policy passage scored above the similarity threshold for this incident. AI analysis is unavailable without a policy context to cite.</div>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            f'<div class="gb-section-header">{ICON_POLICY} {len(matched_policies)} Policy Passage{"s" if len(matched_policies) != 1 else ""} Retrieved</div>',
            unsafe_allow_html=True,
        )
        render_policy_cards(matched_policies)

# ── Decision & Audit Tab ─────────────────────────────────────────────────────
with decision_tab:
    st.markdown(
        f'<div class="gb-section-header">{ICON_SCALE} Human Approval Gate &mdash; Simulation Only</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        f"""
        <div class="gb-decision-action">
            <div class="label">Proposed Simulated Action</div>
            <div class="value">{analysis['suggested_action']}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown(
        f'<div class="gb-sim-disclaimer">{ICON_LOCK} This is a demonstration-only simulation. Approving or rejecting does not revoke a session, reset a password, or change any real account or system.</div>',
        unsafe_allow_html=True,
    )

    can_decide = can_record_decision(
        st.session_state.report,
        st.session_state.report_context_id,
        current_context_id,
        st.session_state.active_report_id,
        st.session_state.decision,
    )

    if not can_decide:
        if st.session_state.decision:
            st.markdown(
                f'<div class="gb-gate-state gb-gate-used">{ICON_INFO} A decision is already recorded for this AI analysis. Run a new analysis to enable one new simulated decision.</div>',
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                f'<div class="gb-gate-state gb-gate-locked">{ICON_ALERT_CIRCLE} Approve and Reject unlock only after a current, citation-validated AI report is available. Complete the AI analysis step first.</div>',
                unsafe_allow_html=True,
            )

    approve_col, reject_col = st.columns(2)
    with approve_col:
        if st.button(
            "Approve Simulated Response",
            disabled=not can_decide,
            use_container_width=True,
        ):
            audit_decision(
                incident,
                "APPROVED",
                "Simulated session-revocation response recorded; no external system was changed.",
                current_context_id,
            )
            st.rerun()
    with reject_col:
        if st.button(
            "Reject Recommendation",
            disabled=not can_decide,
            use_container_width=True,
        ):
            audit_decision(
                incident,
                "REJECTED",
                "No action taken; recommendation rejected by demo analyst.",
                current_context_id,
            )
            st.rerun()

    if st.session_state.decision:
        d = st.session_state.decision
        result_class = "result-approved" if d["decision"] == "APPROVED" else "result-rejected"
        result_icon = ICON_CHECK if d["decision"] == "APPROVED" else ICON_CROSS
        st.markdown(
            f"""
            <div class="gb-decision-result">
                <div class="result-label">Decision Recorded</div>
                <div class="{result_class}">{result_icon} <span>{d['decision']}: {d['outcome']}</span></div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # Audit history
    st.markdown(
        f'<div class="gb-audit-header" style="margin-top:1rem;">{ICON_AUDIT} Temporary Session Audit History</div>',
        unsafe_allow_html=True,
    )
    if st.session_state.audit:
        st.dataframe(
            st.session_state.audit,
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.markdown(
            '<div class="gb-audit-empty">No analyst decisions have been recorded in this session.</div>',
            unsafe_allow_html=True,
        )
    st.markdown(
        f'<div class="gb-audit-session-note">{ICON_ALERT_CIRCLE} This audit history is in-memory only and resets when the browser session ends or refreshes.</div>',
        unsafe_allow_html=True,
    )

