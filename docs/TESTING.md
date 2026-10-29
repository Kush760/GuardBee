# Testing Record

## Recorded automated result

The current root codebase is verified with unittest discovery from the repository root (after installing `requirements.txt`):

```bash
python -m unittest discover -s tests -v
```

Latest verification in this environment after UI integration: **100 tests passed** (`python -m unittest discover -s tests -v`). Re-run before treating any older count or duration as current. CI uses the same discovery command (Python 3.11 in `.github/workflows/ci.yml`).

## Test modules (current)

| Module | Focus |
| --- | --- |
| `tests/test_engine.py` | Deterministic classification, chronology, burst/sequence thresholds, severity/priority |
| `tests/test_data_loader.py` | Schema validation, partition behavior, policies |
| `tests/test_retrieval.py` | TF-IDF match / threshold / no-match |
| `tests/test_ai_client.py` | Citation gates, mocked provider failures |
| `tests/test_workflow.py` | One-decision / stale-context gates |
| `tests/test_audit_store.py` | SQLite save/reload, uniqueness, secret refusal |
| `tests/test_scenario_fixtures.py` | Scenario corpus expectations (incl. INC-1014 Option B) |
| `tests/test_ui_presentation.py` | Classification/severity presentation helpers |
| `tests/test_app_ui.py` | Headless Streamlit pages, citation lock, SQLite audit history UI |

Exact method names evolve with the suite; discovery is authoritative.

## Manual checks pending authorized configuration

- Streamlit browser startup and workflow regions with the current data (UI teammate).
- Missing-key and no-policy-match UI messages.
- One real Nebius/Nemotron request with a permitted key/account/model.
- Report citation display and decision enablement after that response.
- Simulation-only outcome, one-decision lock, and SQLite audit persistence across browser/app restart.
- Deployment from `main` and access from another browser/device.
