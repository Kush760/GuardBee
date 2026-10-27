# Software Requirements Specification

## System context

GuardBee is a local Python/Streamlit application for synthetic suspicious-login investigation. It reads validated JSON, computes deterministic risk (including `NORMAL` / `SUSPICIOUS` / `INSUFFICIENT_EVIDENCE`), retrieves policy passages locally, optionally calls Nebius Token Factory, and records one simulation-only analyst decision per validated report in local SQLite.

## Interfaces

- **UI:** Single Streamlit entry (`app.py`) with dashboard metrics/filters, Investigate / Policy retrieval tabs, and Decision & audit.
- **Files:** `data/incidents.json` and `data/policies.json`, validated by `data_loader.py` (`app.py` uses partitioned incident loading).
- **Audit store:** `audit_store.py` (stdlib SQLite; default `data/audit.db`, override `GUARDBEE_AUDIT_DB`).
- **AI endpoint:** OpenAI-compatible Nebius Token Factory base URL defined in `ai_client.py`.
- **Secrets:** `NEBIUS_API_KEY` and optional `NEBIUS_MODEL` via Streamlit Secrets or environment variables.

## User characteristics

An analyst should be able to read event timelines and policy excerpts. The user retains the decision authority; GuardBee only recommends a simulated response.

## Constraints and assumptions

- Python, Streamlit, scikit-learn, and OpenAI SDK are required dependencies; SQLite audit uses the standard library.
- A live model request requires valid account-specific access, connectivity, quota, and model availability; none is assumed.
- Simulated audit history persists in SQLite across app restart; session state only mirrors the store for display. Decisions remain simulation-only (no real account or SIEM changes).
- AI citation membership checks do not establish semantic truth for every model claim.

## Traceability

| Requirement area | Modules | Tests |
| --- | --- | --- |
| Data safety | `data_loader.py`, `app.py` | `TestDataValidation`, scenario fixtures |
| Risk and retrieval | `engine.py`, `retrieval.py` | `TestGuardBeeDetectionEngine`, `TestPolicyRetrieval` |
| AI error/citation gate | `ai_client.py` | `TestReportValidation` |
| Decision lock + SQLite audit | `workflow.py`, `audit_store.py`, `app.py` | `TestDecisionWorkflow`, `TestAuditStore` |
