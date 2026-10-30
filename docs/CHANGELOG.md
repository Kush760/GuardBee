# Changelog

## Current MVP (v2.2)

- Streamlit console: Dashboard, Security Incidents, Audit History.
- Deterministic risk scoring with NORMAL / SUSPICIOUS / INSUFFICIENT_EVIDENCE, rule hits, and evidence IDs.
- Local TF-IDF policy retrieval with similarity threshold.
- Optional Nebius Token Factory / Nemotron reports with citation-ID validation.
- Workflow context fingerprint and one simulated decision per validated report.
- UI audit history is session-scoped; `audit_store.py` provides optional SQLite helpers used by tests / future wiring.
- Documentation cleaned for disk implementation accuracy; historical planning/reports moved under `docs/archive/`.

## Notes

Older publish/demo/audit reports under `docs/archive/` describe earlier integration snapshots and must not override current `app.py` behavior.
