# GuardBee — Troubleshooting Guide

**Version:** MVP v2.2

## 1. Application cannot load incident or policy data

**Symptom:** Error on startup; app stops.

**Cause:** `load_incidents` / `load_policies` raised `DataValidationError` (missing file, bad JSON, schema violation, duplicates).

**Fix:** Correct `data/incidents.json` or `data/policies.json`. The UI does not skip invalid incident rows.

## 2. Nebius API key missing

**Symptom:** Sidebar shows no key; AI request errors.

**Fix:** Set `NEBIUS_API_KEY` in `.streamlit/secrets.toml` or the environment. Restart Streamlit.

## 3. AI report fails or is empty

**Possible causes:** HTTP 401/403/404/429, timeout, connection error, empty model content, token budget exhausted (`finish_reason=length`).

**Fix:** Check key/endpoint/model (`NEBIUS_BASE_URL`, `NEBIUS_MODEL`), credits, network; retry. GuardBee does not substitute a fake report.

## 4. Report rejected by citation validation

**Cause:** Malformed EVT/POL tokens, IDs not in the current incident/matched policies, or missing required EVT/POL citation.

**Fix:** Request a new report; ensure policies matched for the incident.

## 5. Approve / Reject locked

**Cause:** No citation-validated report for the current context, or a decision already exists for this report id.

**Fix:** Generate a successful report on this incident; or request a new report after context changes.

## 6. Audit History empty after restart

**Expected:** Current UI stores decisions in `st.session_state.audit` only. SQLite in `audit_store.py` is not wired into `app.py`.

## 7. No policies retrieved

**Cause:** TF-IDF scores below `DEFAULT_MIN_SIMILARITY` (0.08) or empty query/corpus edge cases.

**Effect:** AI and decisions stay unavailable for that incident.

## 8. Dependency / import errors

Reinstall `requirements.txt` in an activated venv matching CI’s Python 3.11+ guidance.
