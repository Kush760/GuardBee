# GuardBee V2.2 — Verified Local Backup & GitHub Publish Report

**Time zone note:** machine times below are UTC; Asia/Calcutta = UTC+5:30.

## Result

**Published successfully** to `https://github.com/Kush760/GuardBee` on branch `cursor/recover-mvp-v22-474a`.

| Item | Value |
| --- | --- |
| Commit | `e706cb774e8c36d278abacaec1865c53a367b750` |
| Previous HEAD | `cf8594ad8f5fedebb1dbf9e76bb0a1db863138b8` |
| Push | `cf8594a..e706cb7` (non-force) — hashes match local/remote |
| Message | Finalize GuardBee MVP v2.2 |

## Backup safety

| Backup | Status |
| --- | --- |
| `/opt/cursor/artifacts/guardbee_preflight_backup_20261027T104504Z/` | Intact (`sha256sum -c` OK) |
| `/opt/cursor/artifacts/guardbee_backend_backup_20261027T113123Z/` | Intact |
| `/opt/cursor/artifacts/guardbee_preexec_backup_20261027T120819Z/` | Intact |
| **New** `/opt/cursor/artifacts/guardbee_prepublish_backup_20261027T123856Z/` | Created + verified before publish |

New backup exclusions (explicit): `.streamlit/secrets.toml`, `.env`, `.venv`/`venv`, `__pycache__`/`*.pyc`.  
Includes: full working tree + `.git`, `data/audit.db`, all-refs bundle, status/diff snapshots. Archive members include `app.py`, `engine.py`, data, tests, docs; secrets absent from archive.

Local recovery copies remain on disk (`GuardBee_MVP_v2.2_recovered/`, ZIPs).

## Files published (root SoT)

Staged intentionally (no `git add -A`):

- App: `app.py`, `engine.py`, `data_loader.py`, `retrieval.py`, `ai_client.py`, `workflow.py`, `audit_store.py`, `ui_presentation.py`
- Data: `data/incidents.json` (13), `data/policies.json` (4)
- Tests: full `tests/` including fixtures and new audit/retrieval/scenario/UI tests
- Docs: updated `docs/*`, README, AGENTS, RECOVERY_NOTES, audit/readiness reports
- Config examples: `.streamlit/secrets.toml.example`, `.streamlit/config.toml`, `.github/workflows/ci.yml`, `requirements.txt`, `.gitignore`

## Files excluded / stopped tracking

- **Never committed:** `.streamlit/secrets.toml`, `.env`, `data/audit.db`, `GuardBee_v2.2_full_backup.bundle`
- **Removed from Git index (kept on disk):** `GuardBee_MVP_v2.2_recovered/**`, `GuardBee_MVP_v2.2_recovered.zip`, `GuardBee_MVP_v2.2_git_ready.zip`, `Guardbee_Final_recovered/**`
- `.gitignore` updated so those recovery paths stay local-only

## Tests & validation

- `python3 -m unittest discover -s tests -v` → **Ran 80 tests — OK** (before and after push)
- JSON: 13 incidents / 4 policies; INC-1011 not in production; INC-1014 → `INSUFFICIENT_EVIDENCE` (Option B)
- Secret scan: no tracked credentials; example file uses placeholders only

## Secret configuration (local only — do not commit)

Expected names from code / example:

- `NEBIUS_API_KEY` (required for live Analyze)
- `NEBIUS_MODEL` (optional; default `nvidia/nemotron-3-super-120b-a12b`)

Local setup after clone:

```bash
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
# Edit locally: set NEBIUS_API_KEY (and NEBIUS_MODEL if needed). Never commit this file.
python3 -m streamlit run app.py
```

Or set the same names as environment variables. This publish phase did **not** create or populate a real `secrets.toml`.

## Limitations

- Live Nebius was not configured or tested in this phase (by design).
- Nested recovery artifacts still exist locally and in prior Git history; they are absent from the new tip.
- Default branch remains `main`; this publish is on feature branch `cursor/recover-mvp-v22-474a` (merge to `main` is a separate human decision).
