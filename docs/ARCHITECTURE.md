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
  W --> S[(Streamlit session audit)]
```

## Module responsibilities

- `app.py`: creates the dashboard, reads safe configuration, handles invalid-data UI state, coordinates analysis, and shows the session audit.
- `data_loader.py`: parses and validates JSON before it reaches the application.
- `engine.py`: creates explainable score, severity, flags, evidence IDs, and suggested action from selected events.
- `retrieval.py`: ranks policies with TF-IDF cosine similarity, returns at most `DEFAULT_TOP_K = 3` passages, and excludes scores below `DEFAULT_MIN_SIMILARITY = 0.08` by default. It never pads results with weaker matches. Ties keep corpus order. Invalid arguments or malformed policy entries raise `TypeError`/`ValueError`. Queries and corpora with no usable terms return no matches.
- `ai_client.py`: builds the guarded provider request and validates current event/policy IDs in a returned report, rejecting unknown, stale, and malformed (disguised) IDs.
- `workflow.py`: fingerprints current evidence/policy context and prevents duplicate/conflicting decisions for the same report.

## State model

Streamlit session state keeps `report`, `report_status`, `report_context_id`, `active_report_id`, `report_sequence`, `decision`, and `audit`. Changing an incident or requesting another analysis clears the active report/decision state. Historical audit entries remain only in the current session.

See [architecture diagram](diagrams/architecture.mmd) and [data flow diagram](diagrams/data_flow.mmd).
