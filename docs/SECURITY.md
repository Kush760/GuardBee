# Security Notes (MVP v2.2)

## Secret management

- Store `NEBIUS_API_KEY` (and optional URL/model) in gitignored `.streamlit/secrets.toml` or environment variables.
- Commit only `.streamlit/secrets.toml.example`.
- CI fails if `.streamlit/secrets.toml` is tracked.
- `ai_client._failure_reason` maps provider errors without echoing raw provider bodies that might repeat credentials.

## API key handling

- `app.py` reads key via `st.secrets` then `os.getenv`.
- Key is passed into `generate_report`; not written into decision records.
- `audit_store.save_decision` refuses payloads containing keys named like `api_key`, `NEBIUS_API_KEY`, `password`, `secret`, `token`.

## Synthetic data boundaries

- Incidents and policies under `data/` are synthetic demo content.
- Do not introduce real user credentials into fixtures or examples.

## Input validation

- JSON loaders reject malformed structure before analysis.
- UI fail-closed load prevents partial use of invalid incident files.
- Retrieval validates argument types before TF-IDF.

## External API considerations

- Live calls only when the analyst requests a report and a key is present.
- Timeouts and retries are bounded in `ai_client.py` (60s timeout, limited retries).
- Treat model output as untrusted text; citations must match current IDs.
- `validate_report_citations` enforces ID membership only. It does **not** strip or reject assertive compromise / overstatement language; analysts must read reports critically.

## Actual security limitations

- No authentication on the Streamlit app itself.
- No encryption-at-rest beyond host filesystem for any local DB file created by `audit_store`.
- Session audit is memory-scoped to the Streamlit session.
- Simulated decisions do not enforce real security controls.
- AI citation gate ≠ content safety or factual correctness gate.
- This document does not claim production readiness or compliance certification.
