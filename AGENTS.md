# GuardBee Agent Instructions

## Scope and source of truth

Work only in this repository. The executable source of truth is `app.py`, `engine.py`, `retrieval.py`, `ai_client.py`, `data_loader.py`, `workflow.py`, `audit_store.py`, `ui_presentation.py`, `data/`, and `tests/`. Read `docs/MVP_SCOPE_v2.2.md`, `docs/ARCHITECTURE.md`, `docs/DECISIONS.md`, and `docs/TASKS.md` before a non-trivial change. Handoff notes: `docs/HANDOFF.md`.

## Module boundaries

- Keep UI/session handling in `app.py`.
- Keep classification/severity display helpers in `ui_presentation.py`.
- Keep risk facts deterministic in `engine.py`; do not move scoring into AI prompts.
- Keep local policy matching in `retrieval.py` and retain the explicit minimum-similarity behavior.
- Keep provider communication and report-ID validation in `ai_client.py`.
- Keep JSON schema checks in `data_loader.py` and approval-context logic in `workflow.py`.
- Keep simulated audit persistence in `audit_store.py` (stdlib SQLite only; no secrets in records). Approved by MVP Scope v2.2.
- Do not add a separate backend service, production security integration, or automatic remediation without an explicit approved scope change.

## Security

Never read, print, commit, or replace `.streamlit/secrets.toml`, `.env`, or credentials. Do not add a key to source, tests, documentation, screenshots, or CI logs. Do not call a live provider unless the human explicitly asks and supplies the required authority.

## Completion gate

For code or data changes, run `python -m unittest discover -s tests -v` using an available environment before reporting completion. Preserve the synthetic-only and simulated-only boundaries. Update the affected documentation when behavior, data contracts, tests, or setup instructions change.
