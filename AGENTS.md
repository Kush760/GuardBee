# GuardBee — Agent Instructions

These instructions apply to AI coding agents and contributors working in the GuardBee repository.

## 1. Project Overview

GuardBee is a Streamlit-based application for investigating synthetic suspicious-login incidents.

The main application entry point is `app.py`.

The application provides three pages:

1. Dashboard
2. Security Incidents
3. Audit History

Its workflow includes deterministic incident analysis, policy retrieval, optional AI report generation, citation validation, simulated decisions, and **session-scoped** audit display in the UI. A SQLite helper module (`audit_store.py`) exists but is **not** imported by the current `app.py`.

## 2. Source of Truth

Always inspect the current source code before modifying application behavior.

| File | Responsibility |
|---|---|
| `app.py` | Streamlit UI, navigation, session state, and application orchestration |
| `engine.py` | Incident analysis |
| `retrieval.py` | Policy retrieval |
| `ai_client.py` | AI report generation and citation validation |
| `data_loader.py` | Incident and policy loading and validation |
| `workflow.py` | Analysis context and decision eligibility |
| `audit_store.py` | SQLite decision persistence helpers (standalone relative to current UI) |
| `ui_presentation.py` | Classification/filter helpers (used by tests; UI inlines similar helpers) |

The implementation is the authority for current behavior. Documentation must not override executable code.

## 3. Application Structure

Preserve the three-page structure unless an explicitly approved change requires otherwise.

### Dashboard

Incident statistics, classification counts, classification chart, recent incidents, navigation.

### Security Incidents

Search, filtering, selection, investigation tabs: Timeline, Rules & Evidence, Relevant Policies, AI Analysis.

### Audit History

Session-stored decisions, filtering, record details, navigation to related incidents. Do not describe SQLite-backed UI persistence unless `app.py` calls `audit_store`.

Do not describe UI elements that are not implemented.

## 4. Data Loading

Current `app.py` calls `load_incidents()` and `load_policies()`.

On `DataValidationError`, display an error and stop. Do not claim partial processing of valid rows from an invalid file via the UI.

`load_incidents_partitioned` exists for callers that need per-record issues; it is not used by current `app.py`.

Do not change loading/validation without approval.

## 5. Deterministic Analysis

Use `analyze_incident()` from `engine.py`. Do not move risk calculation into AI prompts or let AI override classification. Preserve NORMAL, SUSPICIOUS, and INSUFFICIENT_EVIDENCE. Do not treat a risk score as proof of compromise. Do not modify thresholds without approval.

## 6. Policy Retrieval

Use `retrieve_policies()` from `retrieval.py`. Do not invent thresholds or match guarantees; verify code and tests first.

## 7. AI Integration

`generate_report`, `validate_report_citations`, `extract_citation_ids`, `configured_base_url`, `configured_model`.

Keep provider I/O in `ai_client.py`. Preserve citation validation. Citation membership ≠ semantic correctness. Failed/stale reports must not enable decisions. Never expose API keys. Do not make live provider requests unless authorized.

## 8. Decision Workflow

`analysis_context_id`, `build_decision_record`, `can_record_decision`. Preserve one-decision-per-validated-report. Decisions: Approve / Reject (simulated only). No real account actions without approval.

## 9. Audit Persistence

`audit_store.py` exposes `save_decision`, `list_decisions`, `get_decision_by_report_id`.

Current UI appends to `st.session_state.audit` only. Preserve the module interface if used by tests. Never store API keys in audit records. Do not change schema without inspection and approval.

## 10. Session State

Clear stale report/decision context when the incident changes. Associate reports with the correct context. Prevent decisions from another incident’s report.

## 11. Security Requirements

Synthetic data in examples/tests. Never commit real API credentials or expose `.streamlit/secrets.toml`. Do not print secrets. Do not convert simulated decisions into real security actions without approval.

## 12. Documentation Requirements

Update docs when behavior changes; match source; preserve `docs/archive/` as historical; do not invent unverified claims. Product version: **MVP v2.2**.

## 13. Testing Requirements

Inspect tests before logic changes. Preferred command:

```bash
python -m unittest discover -s tests -v
```

Report actual results only. Never invent pass counts or live AI verification.

## 14. Scope Protection

Hackathon MVP: no unapproved SIEM/SOAR, real auth integration, automatic blocking/revocation, or architectural redesign.

## 15. Completion Report

Report files changed, reasons, tests run with actual results, docs updated, limitations, and unverified items.
