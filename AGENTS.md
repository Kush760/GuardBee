# GuardBee Agent Instructions

## Scope and source of truth

Work only in this repository. The executable source of truth is `app.py`, `engine.py`, `retrieval.py`, `ai_client.py`, `data_loader.py`, `workflow.py`, `data/`, and `tests/`. Read `docs/ARCHITECTURE.md`, `docs/DECISIONS.md`, `docs/TASKS.md`, and `docs/HANDOFF.md` before a non-trivial change.

## Module boundaries

- Keep UI/session handling in `app.py`.
- Keep risk facts deterministic in `engine.py`; do not move scoring into AI prompts.
- Keep local policy matching in `retrieval.py` and retain the explicit minimum-similarity behavior.
- Keep provider communication and report-ID validation in `ai_client.py`.
- Keep JSON schema checks in `data_loader.py` and approval-context logic in `workflow.py`.
- Do not add a backend, database, real security integration, or automatic remediation without an explicit approved scope change.

## Security

Never read, print, commit, or replace `.streamlit/secrets.toml`, `.env`, or credentials. Do not add a key to source, tests, documentation, screenshots, or CI logs. Do not call a live provider unless the human explicitly asks and supplies the required authority.

## Completion gate

For code or data changes, run `python -m unittest discover -s tests -v` using an available environment before reporting completion. Preserve the synthetic-only and simulated-only boundaries. Update the affected documentation when behavior, data contracts, tests, or setup instructions change.
