# Handoff

## Current snapshot

The repository root (`/workspace`) is the GuardBee MVP v2.2 source of truth: Streamlit UI (`app.py`), deterministic engine, partitioned JSON loading, TF-IDF retrieval, Nebius/Nemotron client boundary, citation/decision safeguards, SQLite simulated audit (`audit_store.py`), synthetic incidents/policies, fixtures, CI workflow, and documentation (including Scope v2.2).

## Verified locally (backend)

Run from the repository root after `pip install -r requirements.txt`:

```bash
python -m unittest discover -s tests -v
```

The current suite is **80** offline unit tests (deterministic rules, data validation/partition, retrieval, mocked AI failures/citations, workflow gates, SQLite audit, scenario fixtures, UI presentation helpers). Those tests do **not** verify a browser session or a live Nebius account.

## Data and classifications

- Production `data/incidents.json`: **13** valid incidents; incomplete empty-IP `INC-1011` is fixture-only.
- Policies: **4** sample records (`POL-001`…`POL-004`).
- Classifications: `NORMAL` / `SUSPICIOUS` / `INSUFFICIENT_EVIDENCE` from `engine.py`. Burst/fail-then-success rules require **≥3** qualifying failures.
- `INC-1014`: proposal metadata expected `SUSPICIOUS`; approved Option B keeps engine result `INSUFFICIENT_EVIDENCE` (see `docs/SCENARIO_COVERAGE_MATRIX.md`, ADR-010).

## Current blockers / external verification

- A real Nebius API key, enabled account, quota, and account-available NVIDIA model are needed for live provider verification.
- Browser UI / restart E2E and public Streamlit deployment checks are handled separately (UI teammate) and remain pending in this environment.
- Screenshots, video, and final submission materials need observed QA evidence.

## Immediate next actions

1. Review remaining packaging cleanup (CH-05) only with explicit approval; preserve recovery copies until approved.
2. With authorized credentials, verify one model call privately and record only non-secret outcomes.
3. Complete browser demo flow and restart audit-history check on a teammate machine.
4. Re-run the full suite before any merge or release. Do not commit/push without explicit authorization.
