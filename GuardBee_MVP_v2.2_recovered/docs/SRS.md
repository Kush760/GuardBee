# Software Requirements Specification

## System context

GuardBee is a local Python/Streamlit application for synthetic suspicious-login investigation. It reads validated JSON, computes deterministic risk, retrieves policy passages locally, optionally calls Nebius Token Factory, and records one simulation-only analyst decision per validated report.

## Interfaces

- **UI:** Streamlit dashboard with incident selection, investigation, policy, and decision/audit tabs.
- **Files:** `data/incidents.json` and `data/policies.json`, validated by `data_loader.py`.
- **AI endpoint:** OpenAI-compatible Nebius Token Factory base URL defined in `ai_client.py`.
- **Secrets:** `NEBIUS_API_KEY` and optional `NEBIUS_MODEL` via Streamlit Secrets or environment variables.

## User characteristics

An analyst should be able to read event timelines and policy excerpts. The user retains the decision authority; GuardBee only recommends a simulated response.

## Constraints and assumptions

- Python, Streamlit, scikit-learn, and OpenAI SDK are required dependencies.
- A live model request requires valid account-specific access, connectivity, quota, and model availability; none is assumed.
- Audit history resets with the Streamlit session.
- AI citation membership checks do not establish semantic truth for every model claim.

## Traceability

| Requirement area | Modules | Tests |
| --- | --- | --- |
| Data safety | `data_loader.py`, `app.py` | `TestDataValidation` |
| Risk and retrieval | `engine.py`, `retrieval.py` | `TestGuardBeeRulesAndRetrieval` |
| AI error/citation gate | `ai_client.py` | `TestReportValidation` |
| Decision lock | `workflow.py`, `app.py` | `TestDecisionWorkflow` |
