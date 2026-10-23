# GuardBee Testing and Submission Guide

## Automated tests

Run the repository suite from the project root:

```powershell
py -m pytest -v
```

The tests are offline. They use synthetic JSON and mock the provider client, so they do not require a Nebius key, internet access, or a live model.
`pytest` is declared in `requirements.txt`; install the project dependencies before running the command in a new environment.

Coverage includes:

- high, medium, and low deterministic risk outcomes and a scoring boundary;
- valid, malformed, incomplete, missing, and empty data cases;
- relevant, no-match, empty-query, and threshold-excluded TF-IDF retrieval;
- missing credentials, mocked provider exceptions, and malformed provider responses;
- accepted, missing, fabricated, stale, and unretrieved citation IDs;
- duplicate/conflicting decision prevention, new-analysis behavior, and stale-context rejection.

## Manual verification still required

Automated tests do not prove the browser workflow or a live provider integration. Before a demonstration or deployment, verify manually:

1. Create a local `.streamlit/secrets.toml` from the example without committing it.
2. Confirm the configured Nemotron model is available to the Nebius account and that the account has usable access and quota.
3. Start the application with `streamlit run app.py`.
4. Review each synthetic incident, its timeline, score, evidence IDs, and displayed policy matches.
5. Request one live report and confirm it cites only IDs shown for the selected incident and retrieved policies.
6. Confirm Approve and Reject are unavailable before a valid report, permit one decision after a valid report, and relock after it.
7. Confirm the audit entry says simulation-only and that no real account or system changed.
8. Refresh or end the session and confirm temporary audit history is not represented as persistent storage.

## Submission readiness checklist

Before publishing or submitting, confirm the following facts rather than claiming them in advance:

- The public repository contains source, tests, documentation, license, and no credential files.
- A deployment URL exists and is tested from a separate browser or device.
- The live Nebius/NVIDIA flow has been exercised with a permitted account and model.
- The demo clearly identifies all data and outcomes as synthetic and simulated.
- README setup steps work from a clean environment.
- A short demonstration shows the complete analyst workflow and states the temporary-audit limitation.

This repository does not create a release archive or deployment automatically. Produce any final ZIP only after these checks are complete.
