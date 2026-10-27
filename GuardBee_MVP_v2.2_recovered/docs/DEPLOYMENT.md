# Deployment

## Local run

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .streamlit\secrets.toml.example .streamlit\secrets.toml
streamlit run app.py
```

Set `NEBIUS_API_KEY` and optionally `NEBIUS_MODEL` only in the ignored local secrets file or host secret manager. The code does not support `NEBIUS_BASE_URL` or `NEMOTRON_MODEL` environment overrides.

## Streamlit Community Cloud

1. Push reviewed source to the protected `main` branch.
2. Create a Streamlit Community Cloud app from the repository and `app.py` entry point.
3. Enter the key and optional model in the host Secrets interface; never commit them.
4. Verify data loading, safe failure behavior, and an authorized live request from a separate browser/device.

## CI overview

`.github/workflows/ci.yml` installs declared dependencies, validates both JSON collections through `data_loader.py`, fails if `.streamlit/secrets.toml` is tracked, and runs the full unittest suite on pushes and pull requests targeting `main`.

No public deployment is represented as complete in this repository.
