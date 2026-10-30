# GuardBee Quick Start

**MVP v2.2**

## Prerequisites

- Python 3.11+ recommended (CI uses 3.11)
- Network access only if you will request a live Nebius AI report

## Environment setup

```powershell
cd E:\Hackathon\Guardbee
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

## Secrets

```powershell
Copy-Item .streamlit\secrets.toml.example .streamlit\secrets.toml
```

Edit `.streamlit/secrets.toml` (gitignored):

```toml
NEBIUS_API_KEY = "your-token-factory-key"
# Optional:
# NEBIUS_BASE_URL = "https://api.tokenfactory.nebius.com/v1/"
# NEBIUS_MODEL = "nvidia/nemotron-3-super-120b-a12b"
```

Without a key, the app still loads and runs deterministic analysis; AI report requests fail with a clear error.

## Start the app

```powershell
streamlit run app.py
```

Open the URL Streamlit prints (typically `http://localhost:8501`).

## Basic usage

1. **Dashboard** — KPIs, classification overview, recent incidents.
2. **Security Incidents** — search/filter, select an incident, review Timeline / Rules & Evidence / Relevant Policies / AI Analysis.
3. Click **Request AI Report** when policies matched and a key is configured.
4. After a citation-validated report, use **Approve** or **Reject** (simulated).
5. **Audit History** — decisions recorded in this browser session only.

## Common startup issues

| Symptom | Likely cause | What to do |
|---|---|---|
| App stops with validation error | Invalid `data/incidents.json` or `policies.json` | Fix JSON; load is fail-closed |
| No Nebius key warning | Missing secret/env | Add `NEBIUS_API_KEY` locally |
| AI report error / empty | Key, quota, model, network, or token budget | See sidebar model; retry; check `docs/TROUBLESHOOTING.md` |
| Approve/Reject locked | No validated report for current context | Generate a successful report first |
| Audit empty after restart | Session-only storage | Expected for current UI |

## CI (local equivalent)

```powershell
python -c "from pathlib import Path; from data_loader import load_incidents, load_policies; load_incidents(Path('data/incidents.json')); load_policies(Path('data/policies.json'))"
python -m unittest discover -s tests -v
```

## More detail

- [docs/DEMO_GUIDE.md](docs/DEMO_GUIDE.md)
- [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md)
- [docs/USER_GUIDE.md](docs/USER_GUIDE.md)
