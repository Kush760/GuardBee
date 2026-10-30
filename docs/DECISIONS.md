# Architectural Decisions (MVP v2.2)

Verified against the current local modules. No fabricated ADR owners or dates.

## Verified decisions (current code)

| Decision | Choice | Evidence |
|---|---|---|
| UI framework | Streamlit multipage via `st.navigation` | `app.py` |
| Risk vs AI | Deterministic engine owns classification; AI explains | `engine.py`, `ai_client.py`, `app.py` |
| Policy search | Local TF-IDF + cosine; threshold 0.08; top_k 3 | `retrieval.py` |
| AI provider | Nebius Token Factory / Nemotron via OpenAI client | `ai_client.py` |
| Citation gate | Reject malformed/unknown IDs; require ≥1 EVT and ≥1 POL (no compromise-phrase regex) | `validate_report_citations` |
| Decision lock | One decision per validated report/context | `workflow.py` + `app.py` |
| Incident load in UI | Fail-closed `load_incidents` | `app.py`, `data_loader.py` |
| Audit in UI | Session list only | `app.py` (`session_state.audit`) |
| SQLite audit | Implemented as standalone module | `audit_store.py` (unused by UI) |
| Simulation boundary | Approve/Reject never call external remediation | `build_decision_record`, UI copy |

## Historical / superseded notes

Older docs and archived reports described SQLite-backed Audit History and partitioned incident loading in the UI. Those match **published** patterns on some commits and the standalone APIs, but **not** the current local `app.py` integration. Keep archival copies under `docs/archive/`; do not treat them as current behavior.
