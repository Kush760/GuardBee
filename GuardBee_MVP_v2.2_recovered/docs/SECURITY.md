# Security and Safety

## Secrets

`.gitignore` excludes `.streamlit/secrets.toml` and `.env`. The application reads `NEBIUS_API_KEY` from Streamlit Secrets or environment variables and never writes it. Use the tracked `secrets.toml.example` only as a template; it contains no real credential.

## Synthetic-only data

The repository contains fabricated account names and RFC 5737 documentation-range examples. Do not replace them with employee, customer, or production security records. `data_loader.py` validates structure, but contributors remain responsible for keeping future samples synthetic.

## AI guardrails

The system prompt treats supplied evidence and policy text as untrusted data, not instructions. It forbids invented facts and completed-action claims, requires citations, and separates observed evidence from potential impact. Report validation rejects invalid IDs but does not prove semantic truth; analysts must review the cited source material.

## No real-world action

The only available outcomes are simulated. GuardBee has no API, code path, credential, or integration for session revocation, password reset, account suspension, or infrastructure modification.
