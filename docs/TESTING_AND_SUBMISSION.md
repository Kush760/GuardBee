# Testing and Submission (MVP v2.2)

## Automated test command

From the repository root (after `pip install -r requirements.txt`):

```bash
python -m unittest discover -s tests -v
```

CI (`.github/workflows/ci.yml`) runs the same discovery on Python 3.11, plus `load_incidents` / `load_policies` on `data/*.json`, and asserts secrets.toml is untracked.

**Do not treat older pass counts in archived reports as current.** Re-run locally and record the observed result before submission claims.

## Test categories (modules present)

| Module | Focus |
|---|---|
| `test_engine.py` | Deterministic analysis |
| `test_data_loader.py` | Validation / partition APIs |
| `test_retrieval.py` | TF-IDF behavior |
| `test_ai_client.py` | Citations / mocked provider |
| `test_workflow.py` | Decision gates |
| `test_audit_store.py` | SQLite module behavior |
| `test_scenario_fixtures.py` | Fixture expectations |
| `test_ui_presentation.py` | Presentation helpers |
| `test_app_ui.py` | Headless Streamlit flows |

Strategy (consolidated from former TEST_PLAN): offline unit tests and mocks only; tests must not require a real API key or network.

## Configuration checks

- `.streamlit/secrets.toml` exists locally only if needed; never commit it.
- Example secrets file remains tracked without real keys.
- Optional: `NEBIUS_BASE_URL`, `NEBIUS_MODEL` for account-specific endpoints.

## Application verification (manual)

Observe, do not invent:

1. App starts and Dashboard renders with loaded incidents.
2. Investigation tabs populate from engine + retrieval.
3. Missing key → AI error path without fabricated report.
4. With authorized key: one live report; citation gate behavior.
5. Approve/Reject lock/unlock rules.
6. Audit History shows session records; restart clears them (current UI).

## Submission preparation

- Confirm MVP labeled **v2.2**.
- README + QUICKSTART runnable by a judge.
- Scope exclusions clear (no real containment).
- Historical materials under `docs/archive/` if needed for evidence, not as current architecture truth.
- Re-run unittest and paste **actual** output into your submission notes.

## Honest verification status

| Check | Status in this documentation pass |
|---|---|
| Docs rewritten to match disk seven modules + `app.py` wiring | Done |
| Unittest suite executed in this pass | **Not run** (protected test tree; no invented PASS) |
| Live Nebius verification | **Not claimed** |
| Browser demo verification | **Not claimed** |
