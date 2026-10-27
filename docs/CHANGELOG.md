# Changelog

## Current MVP (v2.2)

- Built GuardBee as a Streamlit synthetic suspicious-login investigation demo.
- Added deterministic risk scoring with `NORMAL` / `SUSPICIOUS` / `INSUFFICIENT_EVIDENCE`, local TF-IDF policy retrieval, optional Nebius/Nemotron client boundary, and human simulation.
- Persisted simulated Approve/Reject decisions in local SQLite via `audit_store.py` (session state mirrors the store; not session-only).
- Bundled 13 production incidents and 4 sample policies; incomplete empty-IP case remains fixture-only.
- Documented INC-1014 Option B: proposal metadata vs ≥3 failure rule threshold (`docs/SCENARIO_COVERAGE_MATRIX.md`, ADR-010).

## Reliability and safety updates

- Added single-decision report lock to prevent duplicate/conflicting simulation outcomes.
- Added `0.08` minimum TF-IDF similarity and explicit no-match behavior.
- Added JSON schema validation, incident partition loading in `app.py`, and safe UI stop paths.
- Strengthened current-context event/policy citation checks.
- Expanded the unit suite to **80** tests at the repository root (unittest discovery).

## Documentation and delivery assets

- Added structured project, technical, team, quality, diagram, CI, and handoff documentation.
- CH-06/CH-07: README/setup and docs consistency with Scope v2.2 (removed obsolete session-only audit claims from active docs).
