# GuardBee — Security Analytics Console

**MVP v2.2** · Synthetic suspicious-login investigation demo (Streamlit)

GuardBee helps an analyst review synthetic login incidents using deterministic risk analysis, local policy retrieval, optional AI explanation via Nebius Token Factory (NVIDIA Nemotron), and simulated Approve/Reject decisions.

It does **not** monitor live systems, access real authentication services, or execute account containment.

## Capabilities

- Validate and load synthetic incident/policy JSON (`data_loader.py`)
- Deterministic risk, classification, severity, and evidence IDs (`engine.py`)
- TF-IDF policy retrieval with a configurable similarity floor (`retrieval.py`)
- Optional live AI reports with citation-ID validation (`ai_client.py`)
- Context fingerprinting and one-decision-per-validated-report gating (`workflow.py`)
- Session-scoped simulated audit history in the Streamlit UI (`app.py`)

## Technology stack

| Layer | Choice |
|---|---|
| UI | Streamlit (`app.py`) |
| Charts | Altair |
| Risk | Pure Python rules in `engine.py` |
| Retrieval | scikit-learn TF-IDF + cosine similarity |
| AI | OpenAI-compatible client → Nebius Token Factory |
| Audit module | SQLite helpers in `audit_store.py` (module present; **not** called by current `app.py`) |

## High-level architecture

```text
Analyst → app.py (Dashboard | Security Incidents | Audit History)
            ├─ data_loader.py → data/incidents.json, data/policies.json
            ├─ engine.py → analyze_incident
            ├─ retrieval.py → retrieve_policies
            ├─ ai_client.py → generate_report + validate_report_citations
            └─ workflow.py → context id + decision gate
                 └─ session_state.audit (UI persistence only)
```

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) and [docs/diagrams/](docs/diagrams/).

## Quick start

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .streamlit\secrets.toml.example .streamlit\secrets.toml
# Edit secrets.toml: set NEBIUS_API_KEY (optional until you request an AI report)
streamlit run app.py
```

Details: [QUICKSTART.md](QUICKSTART.md).

## Configuration

| Setting | Source | Purpose |
|---|---|---|
| `NEBIUS_API_KEY` | `.streamlit/secrets.toml` or environment | Required for live AI reports |
| `NEBIUS_BASE_URL` | secrets or env (optional) | Override Token Factory base URL |
| `NEBIUS_MODEL` | secrets or env (optional) | Override model id |
| `GUARDBEE_AUDIT_DB` | environment (optional) | Path override for `audit_store.py` only |

Never commit `.streamlit/secrets.toml`.

## Documentation map

| Doc | Contents |
|---|---|
| [docs/MVP_SCOPE_v2.2.md](docs/MVP_SCOPE_v2.2.md) | In/out of scope |
| [docs/TECHNICAL_OVERVIEW.md](docs/TECHNICAL_OVERVIEW.md) | Engine, retrieval, AI, workflow |
| [docs/DATA_MODEL.md](docs/DATA_MODEL.md) | JSON and analysis shapes |
| [docs/VALIDATION_CONTRACT.md](docs/VALIDATION_CONTRACT.md) | Loader rules |
| [docs/DEMO_GUIDE.md](docs/DEMO_GUIDE.md) | Demo walkthrough |
| [docs/SECURITY.md](docs/SECURITY.md) | Secrets and boundaries |
| [docs/TESTING_AND_SUBMISSION.md](docs/TESTING_AND_SUBMISSION.md) | Tests and submission prep |
| [docs/archive/](docs/archive/) | Historical reports and planning snapshots |

## Important limitations

- Synthetic data only; classifications are not proof of compromise.
- AI reports are optional; citation checks prove ID membership, not semantic truth, and do not block compromise-style wording beyond the prompt.
- Simulated decisions do not change real accounts or sessions.
- Current UI audit storage is **session-only** (cleared on browser/app restart). `audit_store.py` implements SQLite persistence but is not integrated into `app.py`.
- Incident load is **fail-closed**: any invalid incident record stops the app (`load_incidents`). `load_incidents_partitioned` exists in `data_loader.py` but is not used by `app.py`.

## License

See [LICENSE](LICENSE).
