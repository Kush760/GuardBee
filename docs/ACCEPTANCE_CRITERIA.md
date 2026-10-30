# Acceptance Criteria (MVP v2.2)

## Definition of done (implementation-backed)

- [x] Synthetic incidents and policies load only after validation (`load_incidents` / `load_policies`).
- [x] Invalid data fails closed in the UI (`DataValidationError` → stop).
- [x] Deterministic risk and evidence are visible before AI (`engine.py` via investigation tabs).
- [x] Policy passages retrieved locally with TF-IDF threshold (`retrieval.py`).
- [x] AI reports are optional, live-only, and citation-gated (`ai_client.py`).
- [x] Simulated Approve/Reject require a current validated report (`workflow.py` + `app.py`).
- [x] Audit History lists session decisions and states simulation-only / session storage limits.
- [x] Secrets example tracked; real `secrets.toml` gitignored.
- [x] CI workflow installs deps, validates JSON loaders, runs unittest discovery.

## Explicit non-goals (must remain false)

- [ ] Real account containment or session revocation
- [ ] Silent fabrication of AI reports on provider failure
- [ ] Claiming SQLite UI persistence while `app.py` does not call `audit_store`

## Verification reminders

Checkboxes above describe **code presence**, not a claim that unittest or live Nebius checks were re-run in the latest docs pass. Record fresh test evidence in submission notes.
