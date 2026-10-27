# Architecture

GuardBee separates deterministic security facts from optional generative explanation. The Streamlit layer coordinates presentation and session state; pure modules remain independently testable.

```mermaid
flowchart LR
  I[(incidents.json)] --> D[data_loader.py]
  P[(policies.json)] --> D
  D --> A[app.py]
  A --> E[engine.py]
  A --> R[retrieval.py]
  E --> W[workflow.py]
  R --> W
  A --> C[ai_client.py]
  C --> N[Nebius Token Factory / NVIDIA Nemotron]
  W --> S[(audit_store.py / SQLite)]
```

## Module responsibilities

- `app.py`: creates the dashboard, reads safe configuration, handles invalid-data UI state, coordinates analysis, and hydrates/displays SQLite audit history.
- `data_loader.py`: parses and validates JSON; partitioned incident load returns valid rows plus explicit issues (`docs/VALIDATION_CONTRACT.md`).
- `engine.py`: creates explainable classification, score, severity, investigation priority, flags, evidence IDs, and suggested action from selected events (chronological, windowed rules).
- `retrieval.py`: ranks policies with TF-IDF and excludes scores below `0.08` by default.
- `ai_client.py`: builds the guarded provider request and validates current event/policy IDs in a returned report.
- `workflow.py`: fingerprints current evidence/policy context and prevents duplicate/conflicting decisions for the same report.
- `audit_store.py`: persists simulated decisions with stdlib SQLite (one row per `report_id`; no secrets).

## State model

Streamlit session state keeps `report`, `report_status`, `report_context_id`, `active_report_id`, `report_sequence`, `decision`, and `audit`. Changing an incident or requesting another analysis clears the active report/decision state. On startup, `audit` is hydrated from SQLite so history survives process restart.

See [architecture diagram](diagrams/architecture.mmd) and [data flow diagram](diagrams/data_flow.mmd).
