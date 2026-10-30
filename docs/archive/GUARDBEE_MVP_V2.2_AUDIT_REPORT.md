# GuardBee MVP v2.2 — Complete Recovery Audit & Change-Count Report

**Audit date:** 2026-10-27 (Asia/Calcutta)  
**Mode:** Audit-only (no source, test, dataset, docs, or Git mutations)  
**Auditor context:** Cloud agent workspace inspecting `Kush760/GuardBee`

---

## 1. Executive summary and verdict

### Verdict

**`READY AFTER SPECIFIED FIXES`**

### Why

The **recovered MVP package** (`GuardBee_MVP_v2.2_recovered/`) implements the core v2.2 behaviors (classification, chronology, burst window, hybrid scoring, partition load, TF-IDF retrieval, citation-gated AI, SQLite audit, single-page UI regions) and currently passes **80/80** unit tests. It is **not** yet submission-ready because:

1. **Repository source of truth is still the pre-v2.2 root tree** (`4f64b20` modules). Root CI validates the incomplete baseline (25 tests), not the recovered package.
2. **Authoritative incident proposal is now available** and proves the recovered `data/incidents.json` / fixtures are **not** the original dataset: only **3/13** production cores match byte-for-content; **INC-1014** fixture expectations were altered to fit the engine (`INSUFFICIENT_EVIDENCE`) while the proposal expects `SUSPICIOUS`.
3. **Browser UI / restart / live Nebius** were **not** executed in this audit (`NOT VERIFIED`).
4. **Recovery ZIP archives are tracked** in the recovery branch; submission layout must not ship nested duplicate projects + archives as the product root.

The uploaded **PDF scope file is present** but could **not** be machine-text-extracted in this environment without installing PDF libraries (disallowed without approval). Scope requirements below are traced primarily from `GuardBee_MVP_v2.2_recovered/docs/MVP_SCOPE_v2.2.md` (claims “MVP scope reference v2.2”), cross-checked against the user audit checklist and the uploaded proposal JSON. Treat PDF text parity as **not independently verified** here.

### Dual-tree fact (critical)

| Tree | Role today | MVP v2.2 complete? |
| --- | --- | --- |
| `/workspace` root (also `main` @ `4f64b20`) | What `streamlit run app.py` and root CI exercise | **No** |
| `/workspace/GuardBee_MVP_v2.2_recovered/` | Recovered package on PR branch | **Mostly yes** (dataset provenance + packaging gaps) |

---

## 2. Repository / recovery integrity

### Git state (observed)

| Item | Value |
| --- | --- |
| Repo root | `/workspace` |
| Current branch | `cursor/recover-mvp-v22-474a` |
| HEAD | `cf8594ad8f5fedebb1dbf9e76bb0a1db863138b8` |
| Tracking | `origin/cursor/recover-mvp-v22-474a` (up to date) |
| `main` | `4f64b20` — `feat: complete GuardBee MVP, 25 unit tests, and full documentation` |
| Working tree | Clean except **untracked** `GuardBee_v2.2_full_backup.bundle` |
| Staged changes | None |
| Remote | `origin` → `https://github.com/Kush760/GuardBee` (token redacted) |
| PR | [#1](https://github.com/Kush760/GuardBee/pull/1) OPEN — base `main`, head `cursor/recover-mvp-v22-474a` |
| Commit `ffce0f1` | **Absent** (`git cat-file` fails; not in available history) |
| `Guardbee_Final/` | **Absent** |

### Authoritative uploads (this audit)

| File | Path | Notes |
| --- | --- | --- |
| Scope PDF | `/home/ubuntu/.cursor/projects/workspace/uploads/GuardBee_MVP_Scope_fb0a.pdf` (36 808 B) | Present; text extraction failed without PDF libs |
| Proposal JSON | `/home/ubuntu/.cursor/projects/workspace/uploads/incidents_revised_proposal_84c1.json` | **sha256 `3ec66eaea8035c1444c10ab68b8d8f03f2f8bf7a6654c57e4dc1243e8c2f16ac`**, 27 157 B, 14 incidents / 59 unique events |

### Recovery package

| Artifact | Status |
| --- | --- |
| `GuardBee_MVP_v2.2_recovered.zip` | Present, **99 070 B**, non-empty |
| `GuardBee_MVP_v2.2_git_ready.zip` | Identical twin of recovered ZIP |
| Extracted tree | `GuardBee_MVP_v2.2_recovered/` |
| `RECOVERY_NOTES.md` | Present; discloses reconstructed INC-1004…1013 fields |
| ZIP ↔ extracted | **68/68 files SHA-identical** (verified this audit) |

### File origin classification

| Class | Items |
| --- | --- |
| **Original (root / `main`)** | Baseline `engine.py` (2 977 B), `app.py` (9 721 B), 3-incident `data/incidents.json`, 4-module tests, no `audit_store` / `ui_presentation` |
| **Recovered (session code sizes match prior Final listing)** | Recovered `engine.py` (12 040), `app.py` (14 578), `ai_client.py` (8 826), `audit_store.py`, `data_loader.py`, `retrieval.py`, `workflow.py`, `ui_presentation.py`, enriched `policies.json`, most tests |
| **Reconstructed (not identical to proposal)** | Recovered `data/incidents.json`, `tests/fixtures/scenario_*.json`, `incomplete_ip_incident.json` (see §4) |
| **Missing** | `ffce0f1`, original `Guardbee_Final/`, original non-empty pre-reset ZIP bytes, PDF machine-readable text in this env |

### Important replacements / losses

- Root production dataset remains **3 incidents**; recovered package has **13** but **≠** uploaded proposal for most records.
- Recovery branch **adds** nested project + ZIPs without promoting modules to root → risk of submitting/running the wrong tree.
- Bundle `GuardBee_v2.2_full_backup.bundle` only contains baseline `4f64b20` (not `ffce0f1`).

---

## 3. Requirements traceability matrix

**Scope source used:** `docs/MVP_SCOPE_v2.2.md` in the recovered package (+ audit checklist).  
**PDF:** uploaded but **text not verified** here.  
**Evaluation target:** recovered tree unless noted as **ROOT**.

Status key: `PASS` | `PARTIAL` | `FAIL` | `NOT VERIFIED` | `NOT APPLICABLE`

| ID | Requirement (faithful summary) | Evidence | Status | Defect / missing | Change needed? | Blocker? |
| --- | --- | --- | --- | --- | --- | --- |
| R01 | Static synthetic `data/incidents.json`; validate inputs | Recovered loader + 13 incidents; ROOT has 3 | **PARTIAL** | Recovered dataset ≠ proposal; ROOT incomplete | Restore proposal cores into SoT dataset | Yes |
| R02 | Valid/invalid partition; no silent drop; report invalids | `data_loader.partition_incidents`; `app.py` captions | **PASS** (recovered) | ROOT lacks partition path | Promote recovered loader/UI | Yes (for root) |
| R03 | Classify NORMAL / SUSPICIOUS / INSUFFICIENT_EVIDENCE | `engine.analyze_incident` | **PASS** (recovered) | ROOT has no classification | Promote engine | Yes (for root) |
| R04 | Chronological event ordering | `_sort_events_chronologically`; tests | **PASS** | INC-1014 proposal chronology intent vs 2-failure weakness | Dataset/expectation policy decision | Partial |
| R05 | Configurable short failure-burst window | `DEFAULT_FAILURE_BURST_WINDOW_MINUTES=30`; tests | **PASS** | — | — | No |
| R06 | Longer-term patterns separately | `GB-RULE-006` | **PASS** | — | — | No |
| R07 | Known-IP failures → success contextual | RULE-003 known=25 pts; INC-1006/1012 | **PASS** (behavior) | Timestamps/IDs diverge from proposal on several rows | Restore proposal events | Yes (data integrity) |
| R08 | Unfamiliar success alone → insufficient | RULE-002 0 pts; INC-1002/1007 | **PASS** | — | — | No |
| R09 | Contextual scoring + evidence IDs | `rule_hits[].evidence_ids` | **PASS** | — | — | No |
| R10 | Duplicate-evidence protection; cap 100 | Failure-set dedupe; `min(score,100)` | **PASS** | Dead `scored_failure_ids` unused | Optional cleanup | No |
| R11 | Separate score / severity / priority | Distinct fields; severity `None` if not SUSPICIOUS | **PASS** | Priority ignores asset criticality (ADR-009 intentional) | Doc clarify only | No |
| R12 | HIGH≥70 / MEDIUM 30–69 / LOW<30 | `_severity_for_suspicious` | **PASS** | No SUSPICIOUS+LOW production example | Optional fixture | No |
| R13 | Normal must not get LOW severity / not listed suspicious for score 0 | Tests + UI filter helpers | **PASS** (unit) | UI E2E not run | Manual UI verify | Unverified |
| R14 | Policies from `data/policies.json` | 4 enriched policies load | **PASS** (recovered) | ROOT policies lack enrichment fields | Promote policies | Yes (for root) |
| R15 | Retrieval relevance; separate from detection | `retrieval.py` TF-IDF; engine does not import it | **PASS** | — | — | No |
| R16 | AI grounded in events + retrieved policies | `ai_client.generate_report` prompt payload | **PASS** (static) | Live provider **NOT VERIFIED** | Authorized smoke | Unverified |
| R17 | Citation validation; block unsupported claims | Membership + regex guards | **PASS** (unit) | Regex ≠ full semantic checker | Optional harden | No |
| R18 | Provider failure / unusable output / retry | `AIReportError`; UI unlocks retry via new Analyze | **PASS** (unit/static) | No auto-retry loop (user re-click) | — | No |
| R19 | Stale-report prevention | `workflow.analysis_context_id` + gate | **PASS** (unit) | — | — | No |
| R20 | Dashboard / Incidents / Audit (single-page OK per ADR-008) | `app.py` metrics + tabs | **PASS** (static) | Browser flow **NOT VERIFIED** | Manual E2E | Unverified |
| R21 | Safe rendering of dynamic content | No `unsafe_allow_html` observed | **PASS** (static) | — | — | No |
| R22 | Exactly one simulated Approve/Reject per validated report | workflow + SQLite UNIQUE `report_id` | **PASS** (unit) | UI E2E **NOT VERIFIED** | Manual E2E | Unverified |
| R23 | SQLite audit persists across restart | `audit_store` + hydrate on init | **PASS** (unit) | Restart-in-UI **NOT VERIFIED** | Manual restart test | Unverified |
| R24 | Audit refs, timestamps, evidence/policy IDs, status | schema + `save_decision` | **PASS** (unit) | — | — | No |
| R25 | Secret exclusion / safe config | gitignore secrets; example only; audit refuses key fields | **PASS** | Nested secret keys only lightly refused | Optional | No |
| R26 | Unit / integration / E2E coverage | 80 unit tests OK | **PARTIAL** | No browser E2E; live AI absent | E2E + optional live | Yes (E2E evidence) |
| R27 | README, setup, CI, deployment, scope docs | Present in recovered tree | **PARTIAL** | README/docs drift; root CI wrong target; some docs still “session-only” | Doc + CI fixes | Yes |
| R28 | Correct repo structure; exclude archives/secrets/venvs/dbs/nested dups | Recovery branch tracks ZIPs + nested tree + pointer README | **FAIL** | Nested SoT; tracked recovery ZIPs; root still baseline | Promote + cleanup | Yes |
| R29 | Simulated decisions not real containment | UI captions in `app.py` | **PASS** (static) | — | — | No |
| R30 | On AI failure show error; do not fabricate | `AIReportError` paths | **PASS** (unit) | Live path **NOT VERIFIED** | — | Unverified |

### Status counts (30 assessed)

| Status | Count |
| --- | --- |
| PASS | 20 |
| PARTIAL | 5 |
| FAIL | 1 |
| NOT VERIFIED | 0 as sole status* |
| NOT APPLICABLE | 0 |

\*Several PASS/PARTIAL rows still carry **unverified** UI/live sub-checks (R13/R16/R20/R22/R23/R26/R30). Counting those unverified sub-checks separately: **7**.

**Confirmed missing/defective requirement themes (deduped):** packaging/SoT (R28), authoritative dataset (R01/R07), CI/docs (R27), E2E evidence (R26).

---

## 4. Incident dataset comparison (proposal vs recovered vs root)

### Method

- **Content-level** comparison of stripped cores (`id/title/account/department/known_ips/events[id,time_utc,type,ip,country]`).
- Exact-file equality with historical Final `13427`-byte blob: **not available** (lost); recovered incidents file is **12 046 B**.

### Inventory

| Source | Incidents | Notes |
| --- | --- | --- |
| Proposal (upload) | 14 (1001–1014) | Includes invalid INC-1011 empty IP |
| Root `data/incidents.json` | 3 | Exact core match to proposal 1001–1003 |
| Recovered production | 13 | Excludes 1011 (correct for production) |
| Recovered fixtures | `scenario_incidents` == production; expectations 14 rows; incomplete fixture for 1011 |

### Exact core match (proposal vs recovered production)

| Result | IDs |
| --- | --- |
| **Full core match** | INC-1001, INC-1002, INC-1003 only (**3/13**) |
| **Events match; metadata differs** | INC-1010, INC-1013, INC-1014 |
| **Events differ (reconstructed)** | INC-1004, 1005, 1006, 1007, 1008, 1009, 1012 |
| **Incomplete fixture ≠ proposal** | INC-1011 (title/account/dept/time differ; empty IP + EVT-408 retained) |

### Classification: proposal metadata vs recovered engine

Running recovered `analyze_incident` on **stripped proposal** records:

| ID | Proposal expected | Engine actual | Match? |
| --- | --- | --- | --- |
| INC-1001…1013 (valid) | as proposal | matches proposal expected | **Yes** (all) |
| INC-1011 | INSUFFICIENT_EVIDENCE | INSUFFICIENT_EVIDENCE (raw) / loader reject | Loader reject expected |
| **INC-1014** | **SUSPICIOUS** | **INSUFFICIENT_EVIDENCE** | **No** |

Recovered `scenario_expectations.json` sets INC-1014 to `INSUFFICIENT_EVIDENCE` with `proposal_defect` noting engine-authoritative override. That is a **test/expectation change to fit the implementation**, not identity with the authoritative proposal.

### Scenario-type naming drift

Several fixture `scenario_type` strings differ from proposal (e.g. 1005/1006/1007/1008/1012) while still covering required types asserted in tests.

### Impact

- Recovered dataset is **functionally similar** for many classifications but **not authoritative**.
- Submitting recovered JSON as “original scenarios” would be inaccurate.
- Restoring stripped proposal → production + fixtures is now possible because the upload is present.

---

## 5. Backend and AI findings

### Recovered engine (strengths)

- Chronology sort; 30‑minute burst; RULE-001/002/003/006; known-IP contextual RULE-003; unfamiliar alone insufficient; failure-set dedupe; score cap 100; severity only for SUSPICIOUS; Finance score bonus removed.
- Unit evidence: overlapping, finance parity, chronology, window, cap tests — **pass**.

### Recovered loader / retrieval / AI / workflow / audit

- Partition load with explicit issues — **pass** (unit + static UI wiring).
- TF-IDF + min similarity — **pass**.
- Citation membership, Unicode dash normalization, compromise/unfamiliar overclaim guards — **pass** (unit).
- Stale context + one decision — **pass** (unit).
- SQLite schema with UNIQUE `report_id`, hydrate on startup — **pass** (unit). Live UI restart — **NOT VERIFIED**.

### Root tree contradictions

- Unfamiliar success still **MEDIUM / +40** (`test_unfamiliar_success_is_medium_risk` still green on root).
- No classification / window / RULE-006 / SQLite audit module.
- Finance RULE-004 style scoring still present in baseline engine behavior (root).

### AI live path

- Configuration via secrets/env — static OK.
- **No live paid API calls** performed → Nebius/Nemotron end-to-end **NOT VERIFIED**.

---

## 6. UI and end-to-end findings

### Static UI review (recovered `app.py`)

- Single-page regions: metrics/filter (dashboard), Investigate / Policy / Decision & audit tabs (ADR-008).
- Classification filter; simulation captions; Approve/Reject gated on validated report; SQLite persistence messaging present.
- No `unsafe_allow_html` found.

### Flows **not** executed this audit

1. Launch Streamlit in browser  
2. Click-through dashboard → incident → policies → AI → decision  
3. Restart app and confirm audit rows in UI  

**Do not treat unit-test success as E2E pass.**

---

## 7. Test execution evidence

### Commands run (this audit)

| Command | Target | Result |
| --- | --- | --- |
| `python3 -m compileall -q .` | recovered | exit 0 |
| import core modules | recovered | `IMPORT_OK` (Streamlit ScriptRunContext warnings only) |
| `python3 -m unittest discover -s tests -v` | recovered | **Ran 80 tests — OK** (exit 0) |
| same | root `/workspace` | **Ran 25 tests — OK** (validates **baseline**, not v2.2) |
| Proposal strip → partition/engine | recovered engine | 13 valid / 1 issue (1011); INC-1014 mismatch vs proposal |
| ZIP SHA vs extracted | both ZIPs | 68/68 match |
| Local markdown link check | recovered `*.md` | 35 checked; **3 broken** links to `unnecessary stuff/` |
| Secret filename scan | repo | no tracked `secrets.toml` / `.env` |
| Streamlit smoke / browser | — | **Not run** |
| Live Nebius | — | **Not run** |
| Dependency install | — | **Not performed** this audit (pre-existing user-site packages used for recovered tests) |

---

## 8. Documentation consistency

| Finding | Severity |
| --- | --- |
| Recovered `MVP_SCOPE_v2.2.md` / `VALIDATION_CONTRACT.md` / ADR-006/008/009 largely align with recovered code | OK |
| README still implies “in-session” decision language in places while SQLite is implemented | P1 drift |
| Older docs (`DOCUMENTATION_INVENTORY`, `PROJECT_CHARTER`, `ROADMAP`) still describe session-only/temporary audit | P1 drift |
| Broken links to `unnecessary stuff/` (archive not present in recovered package) | P2 |
| Nested recovered CI duplicates root CI but **GitHub only runs root workflow** | P0 packaging |
| Scope PDF text not independently extracted; recovered MD used as working scope | Evidence gap |

---

## 9. Deduplicated change register

Overlaps were merged when one task fixes multiple matrix rows (e.g. promoting recovered tree closes many ROOT failures for R02–R15).

### Implementation-level tasks

| ID | Priority | Type | Task | Likely files | Depends on | MVP mandatory? |
| --- | --- | --- | --- | --- | --- | --- |
| CH-01 | **P0** | repo | Promote recovered MVP to repository root (or make root entrypoints/CI exclusively target recovered package) so runnable SoT is v2.2 | root modules, `.github/workflows/ci.yml`, README paths | — | **Yes** |
| CH-02 | **P0** | dataset | Replace recovered production/fixture incidents with **stripped** authoritative proposal cores (exclude INC-1011 from production; keep as incomplete fixture) | `data/incidents.json`, `tests/fixtures/scenario_incidents.json`, `incomplete_ip_incident.json` | CH-01 | **Yes** |
| CH-03 | **P0** | dataset/test | Resolve INC-1014: either strengthen proposal events (≥3 failures) to honor expected SUSPICIOUS **or** formally amend scope/proposal acceptance of engine INSUFFICIENT; update expectations accordingly — do not silently keep mismatched “proposal expected” | proposal integration notes, `scenario_expectations.json`, `SCENARIO_COVERAGE_MATRIX.md` | CH-02 | **Yes** |
| CH-04 | **P0** | config | Point CI at the MVP SoT tree (80-test suite + recovered loader schema checks) | `.github/workflows/ci.yml` | CH-01 | **Yes** |
| CH-05 | **P1** | repo cleanup | Remove tracked recovery archives / nested duplicate trees from submission layout (keep artifacts outside product root) | `GuardBee_MVP_v2.2_*.zip`, nested dirs, `Guardbee_Final_recovered/` | CH-01 | **Yes** |
| CH-06 | **P1** | docs | Fix README/setup structure for SQLite audit, partition wording, module list (`ui_presentation`, `audit_store`) | `README.md` | CH-01 | **Yes** |
| CH-07 | **P1** | docs | Reconcile obsolete session-only audit language in older docs | `DOCUMENTATION_INVENTORY.md`, `PROJECT_CHARTER.md`, `ROADMAP.md`, etc. | CH-01 | **Yes** |
| CH-08 | **P1** | test/UI | Execute manual Streamlit E2E checklist (classify filter, AI failure path, one decision, restart persistence) and record evidence | `docs/TESTING_AND_SUBMISSION.md` | CH-01–CH-03 | **Yes** (evidence) |
| CH-09 | **P2** | docs | Fix broken markdown links to missing `unnecessary stuff/` | `README.md`, `GEMINI.md` | CH-05 | Should |
| CH-10 | **P2** | code | Remove or use dead `scored_failure_ids` in `engine.py` | `engine.py` | — | Optional hygiene |
| CH-11 | **P2** | test | Optional SUSPICIOUS+LOW fixture to demonstrate LOW band | fixtures/tests | CH-02 | Optional |
| CH-12 | **P2** | verify | Authorized live Nebius smoke (only with human-supplied credentials) | secrets (local), `ai_client.py` | CH-01 | Optional for offline MVP if failure path demoed |
| CH-13 | **P3** | code | Harden audit secret refusal for nested keys | `audit_store.py` | — | Optional |

### Totals

| Category | Count |
| --- | --- |
| **Confirmed fixes (mandatory MVP)** | **8** (CH-01…CH-08) |
| **Should-fix / hygiene** | **3** (CH-09…CH-11) |
| **Unverified items needing manual/live testing** | **2** (CH-08 evidence collection; CH-12 live provider) — CH-08 also mandatory evidence |
| **Optional improvements** | **2** (CH-12 if offline demo accepted; CH-13) |

**Distinct required implementation tasks for MVP submission:** **8 confirmed** (+ E2E evidence captured under CH-08).  
**Optional:** 3–5 depending on live-AI expectation.

---

## 10. Exact totals summary

### A. Requirement-level

- Assessed: **30**
- PASS: **20**
- PARTIAL: **5**
- FAIL: **1** (R28 structure)
- Additional unverified sub-checks: **7** (UI/live)
- Confirmed defective/missing themes after dedupe: **4** (SoT packaging, authoritative dataset, CI/docs, E2E evidence)

### B. Implementation-level

- Confirmed mandatory fixes: **8**
- Unverified checks requiring manual testing: **UI E2E + restart**; live AI optional/authorized
- Optional improvements: **3+**

---

## 11. Risks, blockers, dependencies, missing evidence

### Blockers for submission

1. Root tree ≠ MVP v2.2 (running/CI wrong code).  
2. Recovered dataset ≠ uploaded authoritative proposal.  
3. INC-1014 proposal vs engine conflict unresolved as an **accepted** scope decision.  
4. No browser E2E evidence.  
5. Recovery ZIPs/nested project pollute submission structure.

### Dependencies

`CH-01` before meaningful CI (`CH-04`) and doc path fixes; `CH-02` before honest scenario claims; `CH-03` before locking expectations; `CH-08` after code/data stabilize.

### Missing evidence

- PDF full-text extraction (tooling not installed).  
- Browser Streamlit session.  
- Live Nebius.  
- Historical `ffce0f1` / Final ZIP bytes (still missing; proposal upload now recovers the dataset authority).

---

## 12. Recommended implementation order

1. **CH-01** Promote recovered code to SoT (no force-push; normal PR merge strategy).  
2. **CH-02** Restore stripped proposal into `data/incidents.json` + fixtures.  
3. **CH-03** Decide/fix INC-1014 expectation vs events.  
4. **CH-04** Fix root CI.  
5. **CH-05** Clean archives/nested duplicates from product root.  
6. **CH-06 / CH-07** Documentation reconciliation.  
7. **CH-08** Manual E2E + restart proof.  
8. Optional CH-09…CH-13.

---

## 13. Submission readiness checklist

- [ ] Repository root runs recovered MVP modules (not baseline `4f64b20` engine/app).  
- [ ] `data/incidents.json` matches stripped authoritative proposal (1011 excluded).  
- [ ] Fixtures/expectations aligned with proposal **or** documented approved deviations (esp. INC-1014).  
- [ ] Root CI runs 80-test MVP suite + JSON validation on SoT paths.  
- [ ] No tracked secrets; audit DB gitignored.  
- [ ] No recovery ZIP / nested duplicate project as the submission root.  
- [ ] README/setup/demo docs match SQLite + partition behavior.  
- [ ] Manual UI E2E recorded (classify, AI fail path, one decision, restart audit).  
- [ ] (If required) Authorized live AI smoke recorded.  
- [ ] Unit tests green on SoT tree.

---

## Appendix A — Integrity quick facts

```
branch: cursor/recover-mvp-v22-474a @ cf8594a
main:   4f64b20
ffce0f1: MISSING
PR: https://github.com/Kush760/GuardBee/pull/1
proposal sha256: 3ec66eaea8035c1444c10ab68b8d8f03f2f8bf7a6654c57e4dc1243e8c2f16ac
recovered unittest: 80 OK
root unittest: 25 OK (baseline)
zip/extracted: 68/68 identical
Guardbee_Final/: ABSENT
```

## Appendix B — What this audit did **not** do

- No file modifications, commits, pushes, merges, resets, or force-pushes.  
- No dependency installs.  
- No live paid API calls.  
- No browser automation.  
- No silent dataset “fixes.”

---

**End of report.**
