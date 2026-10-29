# MVP Workflow

MVP Scope v2.2 §7 names **Dashboard**, **Security Incidents**, and **Audit History** as workflow areas to improve. GuardBee delivers them as three Streamlit navigation views in `app.py` (`st.navigation` / `st.Page`): Dashboard KPIs and recent incidents, Security Incidents investigation (timeline, rules, policies, AI analysis), and Audit History for persisted simulated decisions. See [ADR-008](DECISIONS.md#adr-008-streamlit-navigation-for-mvp-scope-v22--7).

## 1. Security Dashboard

The Dashboard shows total valid incidents, classification counts from `engine.py`, rejected-record count from `load_incidents_partitioned()`, and a classification overview chart. Severity is displayed only when applicable (`N/A` / not assigned for normal and insufficient-evidence cases).

## 2. Incident Investigation

On **Security Incidents**, GuardBee displays the synthetic account, department, classification, investigation priority, severity (or not assigned), chronological event timeline, rule hits, and evidence IDs returned by `engine.py`. No model participates in this step. A risk score is not proof of compromise.

## 3. Company Policy Check

The application creates a query from incident title, department, rule flags, and suggested action. `retrieval.py` returns up to three policies meeting the `0.08` cosine-similarity threshold. A no-match state is shown explicitly.

## 4. AI Security Analysis

When there is a policy match and the analyst clicks **Request AI Report**, GuardBee sends current synthetic incident facts, deterministic analysis, and retrieved policies to the configured Nebius endpoint. Success or failure feedback appears in the investigation view; a report must cite current `EVT-*` IDs and retrieved `POL-*` IDs. Missing credentials, provider failures, malformed output, no policy match, or citation failure keep the report invalid and approval disabled.

## 5. Response and Audit

One validated report can receive either Approve simulated response or Reject recommendation. The app persists a simulated audit event in local SQLite at `data/audit.db` (unique per report ID), hydrates history on startup, and disables both controls for that report. **Audit History** shows evidence IDs, policy IDs, and report context when recorded. A new AI analysis creates a new report ID; selecting a different incident invalidates the active report.

The application performs no real remediation. See [workflow diagram](diagrams/workflow.mmd).
