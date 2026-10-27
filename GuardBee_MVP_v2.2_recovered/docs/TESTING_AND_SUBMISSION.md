# GuardBee Testing and Submission Guide

## Automated tests

The CI workflow and agent completion gate use the unittest discovery command. From the project root (after installing `requirements.txt`):

```powershell
python -m unittest discover -s tests -v
```

On Windows with the Python launcher you may use `py -m unittest discover -s tests -v`.

The tests are offline. They use synthetic JSON and mock the provider client, so they do not require a Nebius key, internet access, or a live model.

`pytest` remains listed in `requirements.txt` as an optional runner. If you prefer pytest, target the `tests/` package only so sibling folders are not collected:

```powershell
python -m pytest tests -v
```

Do not rely on a bare `pytest` invocation from a parent directory that also contains another copy of the suite (for example a local `Guardbee_Final/` tree).

Coverage includes:

- high and medium deterministic severity outcomes, score boundaries, and the coded LOW band for `SUSPICIOUS` scores below 30 (current rule points typically yield MEDIUM or HIGH when suspicious);
- valid, malformed, incomplete, missing, and empty data cases, including partitioned valid/invalid handling;
- relevant, no-match, empty-query, and threshold-excluded TF-IDF retrieval;
- missing credentials, mocked provider exceptions, and malformed provider responses;
- accepted, missing, fabricated, stale, and unretrieved citation IDs (including Unicode-dash normalization);
- duplicate/conflicting decision prevention, new-analysis behavior, and stale-context rejection;
- SQLite audit save/reload across a new connection (simulating app restart) and refusal of secret-bearing fields.

## Manual verification still required

Automated tests do not prove the browser workflow or a live provider integration. Before a demonstration or deployment, verify manually:

1. Create a local `.streamlit/secrets.toml` from the example without committing it.
2. Confirm the configured Nemotron model is available to the Nebius account and that the account has usable access and quota.
3. Start the application with `streamlit run app.py`.
4. Review each synthetic incident, its timeline, score, evidence IDs, and displayed policy matches.
5. Request one live report and confirm it cites only IDs shown for the selected incident and retrieved policies.
6. Confirm Approve and Reject are unavailable before a valid report, permit one decision after a valid report, and relock after it.
7. Confirm the audit entry says simulation-only and that no real account or system changed.
8. Refresh the browser or stop and restart `streamlit run app.py`, then confirm the same simulated decision still appears in **Decision & audit** / audit history (SQLite persistence via `audit_store.py`, default `data/audit.db`, overridable with `GUARDBEE_AUDIT_DB`). History must not disappear merely because the Streamlit session restarted.

## Submission readiness checklist

Before publishing or submitting, confirm the following facts rather than claiming them in advance:

- The public repository contains source, tests, documentation, license, and no credential files.
- A deployment URL exists and is tested from a separate browser or device.
- The live Nebius/NVIDIA flow has been exercised with a permitted account and model.
- The demo clearly identifies all data and outcomes as synthetic and simulated.
- README setup steps work from a clean environment.
- A short demonstration shows the complete analyst workflow and states that simulated audit rows persist in local SQLite across restart (still simulation-only; no real account changes).

This repository does not create a release archive or deployment automatically. Produce any final ZIP only after these checks are complete.
