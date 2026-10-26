# Changelog

## Current MVP

- Built GuardBee as a Streamlit synthetic suspicious-login investigation demo.
- Added deterministic risk scoring, local TF-IDF policy retrieval, optional Nebius/Nemotron client boundary, human simulation, and session audit.

## Reliability and safety updates

- Added single-decision report lock to prevent duplicate/conflicting simulation outcomes.
- Added `0.08` minimum TF-IDF similarity and explicit no-match behavior.
- Added JSON schema validation and safe UI stop path.
- Strengthened current-context event/policy citation checks.
- Expanded the unit suite from 6 to 25 tests.

## Workstream D - policy retrieval and AI boundary hardening

- Citation validation now compares IDs case-insensitively and rejects fabricated IDs hidden by lowercase, Unicode dashes, glued letter/digit/underscore prefixes, or underscore suffixes.
- Added `DEFAULT_TOP_K = 3` to `retrieval.py` (no ranking change). Added argument and policy-entry validation, and empty-vocabulary corpora now return no matches instead of raising.
- Added `tests/test_retrieval.py` and offline provider-boundary tests that drive the OpenAI SDK through a mock HTTP transport. The unit suite grew from 25 to 54 tests.
- Unchanged: TF-IDF retrieval, the `0.08` threshold, bundled-incident policy matches, provider endpoint, model, timeout, retries, and the request payload.

## MVP scope Phase A - UI alignment (`dev`)

- Merged the Workstream B four-view UI (`feature/ui-polish`) into `dev`.
- Fixed a navigation bug where "Open"/"Investigate" bounced back to the previous view, making the incident detail, AI analysis, and decision controls unreachable.
- HTML-escaped all incident, event, policy, AI-status, and audit values rendered as raw HTML.
- Removed the UI rule "Normal = severity LOW"; activity classification and investigation priority are shown only when `engine.py` provides them. Severity counts replace the Suspicious/Normal counts.
- Added a "not proof of compromise" note, the evidence and policies cited by a validated AI report, and an explicit Retry after AI failure.
- The AI prompt now requests Observed facts / Inferred risk / Unknowns and limitations sections. Added `extract_citation_ids()`.
- Added headless Streamlit UI tests (`tests/test_app_ui.py`). The suite grew from 54 to 64 tests.

## Documentation and delivery assets

- Added structured project, technical, team, quality, diagram, CI, and shareable-handoff documentation.
