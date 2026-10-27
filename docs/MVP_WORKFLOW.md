# MVP Workflow

MVP Scope v2.2 §7 names **Dashboard**, **Security Incidents**, and **Audit History** as workflow areas to improve. GuardBee delivers them in **one Streamlit page** (`app.py`): classification metrics and filters (dashboard), the **Investigate** / **Policy retrieval** tabs (security incidents), and the **Decision & audit** tab (audit history). Separate multipage routes are **not** required; see [ADR-008](DECISIONS.md#adr-008-single-page-ui-for-mvp-scope-v22--7).

## 1. Security Dashboard

The analyst filters incidents by classification (`SUSPICIOUS`, `NORMAL`, `INSUFFICIENT_EVIDENCE`, or All). Counts for each classification are shown. Severity is displayed only when applicable (`N/A` for normal and insufficient-evidence cases). Normal activity is not listed under the Suspicious filter.

## 2. Incident Investigation

GuardBee displays the synthetic account, department, classification, investigation priority, severity (or N/A), full event timeline, rule hits, and evidence IDs returned by `engine.py`. No model participates in this step. A risk score is not proof of compromise.

## 3. Company Policy Check

The application creates a query from incident title, department, rule flags, and suggested action. `retrieval.py` returns up to three policies meeting the `0.08` cosine-similarity threshold. A no-match state is shown explicitly.

## 4. AI Security Analysis

When there is a policy match and the analyst clicks Analyze, GuardBee sends current synthetic incident facts, deterministic analysis, and retrieved policies to the configured Nebius endpoint. A report must cite current `EVT-*` IDs and retrieved `POL-*` IDs. Missing credentials, provider failures, malformed output, no policy match, or citation failure keep the report invalid and approval disabled.

## 5. Response and Audit

One validated report can receive either Approve simulated response or Reject recommendation. The app persists a simulated audit event in SQLite (unique per report ID), hydrates history on startup, and disables both controls for that report. A new AI analysis creates a new report ID; selecting a different incident invalidates the active report.

The application performs no real remediation. See [workflow diagram](diagrams/workflow.mmd).
