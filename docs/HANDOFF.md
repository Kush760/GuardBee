# Handoff

## Current snapshot

The repository contains the GuardBee Python/Streamlit MVP, validated synthetic JSON data, deterministic risk engine, local TF-IDF retrieval, Nebius/Nemotron client boundary, citation/decision safeguards, 25 unit tests, diagrams, CI workflow, and documentation.

## Verified locally

The recorded unit-suite baseline is 25 tests passing through `python -m unittest discover -s tests -v`. Those tests verify deterministic rule boundaries, data validation, retrieval behavior, mocked AI failures/citations, and decision-lock behavior. They do not verify a browser session or live Nebius account.

## Current blockers

- A real Nebius API key, enabled account, quota, and account-available NVIDIA model are needed for live provider verification.
- A public Streamlit deployment and external-browser check are still pending.
- Screenshots, video, and final submission details need actual QA evidence.

## Immediate next actions

1. `[Member-Lead]`: review CI/docs and protect `main`.
2. `[Member-AI-1]`: with authorized credentials, verify one model call privately and record only non-secret outcomes.
3. `[Member-UI]` and `[Member-QA-1]`: perform browser flow and prepare the demo from observed behavior.
4. Run the full suite again before any merge or release.
