# GuardBee MVP v2.2 — Master Demo-Readiness Report

**Date:** 27 Oct 2026 (Asia/Calcutta)  
**Workspace:** `/workspace`  
**Branch:** `cursor/recover-mvp-v22-474a`  
**HEAD (committed):** `cf8594ad8f5fedebb1dbf9e76bb0a1db863138b8`  
**Execution mode:** inspect → protect → test → dynamic/browser → E2E → audit (no commit/push per mission)

---

## 1. Final verdict

**READY FOR DEMO**

All in-scope deterministic, UI, workflow, persistence, and offline AI-safety paths verified with evidence. No confirmed in-scope code defects required a Phase 7 fix. Live Nebius/Nemotron remains **NOT VERIFIED** (no credentials in this environment); that is a configuration gap for the live-AI demo beat, not an application defect.

---

## 2. Executive summary

**Verified**

- Root `/workspace` is the runnable SoT: 13 production incidents, 4 policies, INC-1011 fixture-only, INC-1014 Option B (`INSUFFICIENT_EVIDENCE`).
- `python3 -m compileall` OK; **80/80** unit tests OK (baseline and final).
- Streamlit starts (`127.0.0.1:8501`), health `200 ok`; browser checks passed for dashboard, filters, NORMAL / SUSPICIOUS / INSUFFICIENT_EVIDENCE, policy retrieval, missing-key AI failure, locked Approve/Reject, empty audit messaging.
- Offline E2E: load → classify → retrieve → mocked AI success/failure → one simulated decision → duplicate blocked → temp SQLite reopen; production `data/audit.db` unchanged (16384 bytes).
- Secrets not tracked; no secret values printed; both prior backups + new pre-exec backup intact.

**Unverified / residual**

- Live Nebius Token Factory call: **NOT VERIFIED** (no `.streamlit/secrets.toml`, `NEBIUS_API_KEY` unset).
- Browser Approve/Reject after a *live* report: not exercised (requires key); same gates exercised offline with mocks.
- Remote GitHub Actions `verify` is SUCCESS for committed HEAD on PR #1; it does **not** cover the current uncommitted working tree (~50 paths from prior CH recovery).

---

## 3. Backup safety

| Backup | Path | Result |
| --- | --- | --- |
| Prior preflight | `/opt/cursor/artifacts/guardbee_preflight_backup_20261027T104504Z/` | `sha256sum -c SHA256SUMS.txt` OK before and after |
| Prior backend | `/opt/cursor/artifacts/guardbee_backend_backup_20261027T113123Z/` | OK before and after |
| **New pre-execution** | `/opt/cursor/artifacts/guardbee_preexec_backup_20261027T120819Z/` | Created + verified; ~1.4M |

**New backup contents:** `workspace_full_state.tar.gz` (325 members including `engine.py`, `app.py`, `data/incidents.json`, `data/policies.json`, `data/audit.db`, `.git/HEAD`), `guardbee_all_refs.bundle` (`git bundle verify` OK), `BACKUP_MANIFEST.txt`, `SHA256SUMS.txt`, git status/diff/untracked snapshots.

**Explicit exclusions:** `.streamlit/secrets.toml`, `.env`, `.venv`/`venv`, `**/__pycache__`, `*.pyc`.  
**Neither prior backup was overwritten or deleted.**

---

## 4. Static audit results

**Checks performed**

- AST parse / `compileall` on root modules: `app.py`, `engine.py`, `data_loader.py`, `retrieval.py`, `ai_client.py`, `workflow.py`, `audit_store.py`, `ui_presentation.py`.
- Import/path sanity; root CI (`.github/workflows/ci.yml`) installs deps, validates JSON via `data_loader`, blocks tracked secrets, runs `unittest`.
- Schema load: 13 valid / 0 partition errors; policies POL-001…004.
- Engine map: 6 SUSPICIOUS / 3 NORMAL / 4 INSUFFICIENT_EVIDENCE; INC-1014 → `INSUFFICIENT_EVIDENCE` with 2 failures (Option B preserved).
- Security: no `eval`/`exec`/`pickle`/`unsafe_allow_html` in `app.py`; `audit_store` refuses secret-bearing keys; `.streamlit/secrets.toml` / `.env` / `data/audit.db` not tracked.
- Docs: active README/AGENTS describe SQLite audit; “session-only” appears only as historical notes in DECISIONS / inventory / changelog.
- `pip check`: no broken requirements.

**Confirmed findings requiring code fix:** none.

**Unresolved / residual risks (not defects)**

- Live provider availability and account model ID must be confirmed before judges see Analyze succeed.
- Working tree still contains uncommitted recovery/doc/data changes relative to HEAD; demo from `/workspace` as-is (do not `git reset --hard`).

---

## 5. Testing results

| Run | Command | Result |
| --- | --- | --- |
| Baseline | `python3 -m unittest discover -s tests -v` | **Ran 80 tests in ~0.074s — OK** |
| Final (Phase 9) | same | **Ran 80 tests in ~0.085s — OK** |
| Compile | `python3 -m compileall -q` (root modules) | OK |
| Pip | `python3 -m pip check` | No broken requirements |

Artifacts: `/opt/cursor/artifacts/master_baseline_tests.txt`, `master_final_tests.txt`.

No failing tests were weakened or deleted. No new regression tests were required (no confirmed production bugs).

---

## 6. Dynamic / E2E results

### Streamlit runtime

```bash
export GUARDBEE_AUDIT_DB=/tmp/guardbee_master_demo_audit.db
python3 -m streamlit run app.py --server.port 8501 --server.address 127.0.0.1 --server.headless true
```

- `GET /_stcore/health` → **200** body `ok`
- `GET /` → **200**
- No error/traceback/deprecation noise observed in the Streamlit pane during checks

### Browser (real UI automation)

Against `http://127.0.0.1:8501/` — **passed**:

1. Dashboard: GuardBee title, metrics (13 / 6 / 3 / 4), safety banner  
2. Filters: All / SUSPICIOUS / NORMAL / INSUFFICIENT_EVIDENCE  
3. NORMAL (INC-1003, INC-1004): not presented as compromise  
4. SUSPICIOUS (INC-1001, INC-1010): score/evidence/rules shown  
5. INSUFFICIENT_EVIDENCE (INC-1002, INC-1014): uncertain messaging; not automatic malice  
6. Analyze without key: clear `NEBIUS_API_KEY is missing…`; **no fabricated report**  
7. Approve/Reject disabled without validated report  
8. Policy tab: TF-IDF matches with similarity ≥ 0.08  

Screenshots: `/opt/cursor/artifacts/demo_readiness_screenshots/` (35 `.webp` files).

### Offline E2E (temp SQLite)

Scripted workflow: classifications → retrieval → AI missing key / mocked provider fail → mocked grounded report → citation OK → one APPROVED → second decision blocked → reopen DB → **production `data/audit.db` size unchanged**.

No real account blocking, SIEM, or containment invoked.

---

## 7. AI verification

| Mode | Status | Evidence |
| --- | --- | --- |
| Missing API key | **PASS** | Unit tests + browser + scripted `AIReportError` |
| Mocked provider/network failure | **PASS** | Scripted + existing `tests/test_ai_client.py` |
| Citation / hallucination gates | **PASS** | Unit tests + offline E2E |
| Empty/malformed response | **PASS** | Covered by existing unit tests |
| **Live Nebius / Nemotron** | **NOT VERIFIED** | No secrets file; env key unset — by design, no invented credentials |

Default model string in code/docs: `nvidia/nemotron-3-super-120b-a12b` (must be confirmed in the Nebius catalog for the demo account).

---

## 8. Changed files

**This execution made no application code, data, test, or documentation edits.**  
Phase 7 found no confirmed in-scope defects to patch.

Artifacts created outside the repo (not Git changes):

- `/opt/cursor/artifacts/guardbee_preexec_backup_20261027T120819Z/`
- `/opt/cursor/artifacts/GUARDBEE_V2.2_MASTER_DEMO_READINESS_REPORT.md` (this file)
- `/opt/cursor/artifacts/MASTER_DEMO_READINESS_EVIDENCE_LOG.txt`
- `/opt/cursor/artifacts/demo_readiness_screenshots/`
- Test/status snapshots under `/opt/cursor/artifacts/master_*`

Working tree already had ~50 uncommitted paths from prior CH-01…08 recovery (preserved; not reset).

---

## 9. Data integrity

| Asset | Count / hash |
| --- | --- |
| `data/incidents.json` | **13** incidents; SHA-256 `5d187f45a4d2a8ce076a5e10d7f7f664b3276c080c5dbac6855bb36264f6f7db` |
| `data/policies.json` | **4** policies; SHA-256 `f1d1ab56df9c63f123d1c3d1943228a24d16a8d5ea86901ebaddaec484896fa6` |
| INC-1011 | **Not** in production; fixture `tests/fixtures/incomplete_ip_incident.json` |
| INC-1014 | Option B preserved: engine → **`INSUFFICIENT_EVIDENCE`** (2 failures; threshold ≥3 untouched) |
| `data/audit.db` | Present, gitignored; size **16384** before/after (not altered by this run’s temp-DB tests) |

---

## 10. CI / Git status

| Item | Value |
| --- | --- |
| Branch | `cursor/recover-mvp-v22-474a` |
| HEAD | `cf8594ad8f5fedebb1dbf9e76bb0a1db863138b8` |
| Working tree | Dirty (~50 paths); **not committed** (mission rule) |
| Local tests on working tree | 80/80 OK |
| Remote CI | PR [#1](https://github.com/Kush760/GuardBee/pull/1) `verify` **SUCCESS** for that **committed** HEAD (completed 27 Oct 2026 ~15:29 IST / 09:59 UTC) |
| Remote CI on uncommitted tree | **Not run** — do not claim remote green for dirty tree |

---

## 11. Remaining gaps

| Gap | Impact | Smallest resolution |
| --- | --- | --- |
| Live Nebius not verified | Analyze live report + unlock Approve/Reject for judges needs a real key/model | Add local `.streamlit/secrets.toml` (never commit) with working `NEBIUS_API_KEY` / available `NEBIUS_MODEL`; one smoke Analyze on INC-1001 |
| Uncommitted recovery tree | Risk of confusion vs HEAD if someone resets | Keep `/workspace` as demo SoT; commit/PR separately only when humans approve |
| Browser Approve after live report | Not shown in UI this run | Same as live key; offline gates already proven |

---

## 12. Demo run instructions (judges)

```bash
cd /workspace   # or cloned repo root with the recovered tree
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
# Optional for live AI beat:
# cp .streamlit/secrets.toml.example .streamlit/secrets.toml
# edit NEBIUS_API_KEY (+ NEBIUS_MODEL if needed)
python3 -m streamlit run app.py
# equivalent when `streamlit` is on PATH: streamlit run app.py
```

**Suggested scenario order**

1. **Dashboard** — show 13 / 6 / 3 / 4 metrics and safety banner.  
2. **NORMAL** — INC-1004: green banner, no rules fired.  
3. **SUSPICIOUS** — INC-1001: GB-RULE-001 + GB-RULE-003, evidence EVT-*, score 70.  
4. **INSUFFICIENT_EVIDENCE / Option B** — INC-1014: not forced SUSPICIOUS; unfamiliar IP alone / below ≥3 failures.  
5. **Policies** — TF-IDF hits POL-001/002/004.  
6. **Analyze** — with key: grounded report; without key: safe error (still demoable).  
7. **Decision** — one Approve **or** Reject; show SQLite audit row; attempt second decision → blocked.  
8. **Restart app** — audit history still present (`data/audit.db`).

---

## 13. Evidence log

Primary log: `/opt/cursor/artifacts/MASTER_DEMO_READINESS_EVIDENCE_LOG.txt`

Notable commands/outputs:

- Existing backups: `sha256sum -c SHA256SUMS.txt` → OK  
- New backup: `/opt/cursor/artifacts/guardbee_preexec_backup_20261027T120819Z` → ARCHIVE_OK / bundle OK / 325 members  
- `python3 -m unittest discover -s tests -v` → `Ran 80 tests` / `OK` (×2)  
- Streamlit health → `ok`  
- Browser goals 1–8 → PASS (screenshots under `demo_readiness_screenshots/`)  
- Offline E2E → `E2E_OFFLINE_ALL_PASS` / `PASS mocked_ai_report_then_one_decision` / prod audit untouched  
- `LIVE_NEBIUS=NOT_VERIFIED no_secrets_configured`  
- `gh pr view` → CI `verify` SUCCESS on HEAD `cf8594ad…`

---

*Mission constraints honored: no hard reset/clean, no secret exposure, no inventing incidents/provider responses, no commit/push, no real containment, both prior backups preserved.*
