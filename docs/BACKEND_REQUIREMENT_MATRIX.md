# Backend requirement-to-code matrix (local tree)

**Source of truth:** `docs/MVP_SCOPE_v2.2.md`  
**Baseline:** local working directory (includes uncommitted Phase 1 engine/loader + UI files owned by another member)

## Conflict resolution

| Topic | Older docs | Approved scope | Resolution |
| --- | --- | --- | --- |
| Audit persistence | ADR-006 / FR-09 / AGENTS “no DB” | SQLite required (§6, §1.11) | **Scope v2.2 wins.** AGENTS “explicit approved scope change” is satisfied by MVP Scope v2.2. Supersede ADR-006 / FR-09 when implementing SQLite. |
| UI pages | — | §7 | **Out of backend responsibility** for this workstream. |

## Matrix

| ID | Requirement | Code | Tests | Docs | Status |
| --- | --- | --- | --- | --- | --- |
| B-01 | Load static `data/incidents.json` | `data_loader.load_incidents`, `app.py` | `test_data_loader` | DATA_MODEL | **Complete** |
| B-02 | Validate schema; report invalid; do not silent-drop | `IncidentPartitionResult`; `app.py` uses `load_incidents_partitioned` | `test_data_loader` partition suite | `VALIDATION_CONTRACT.md` | **Complete** (B4) |
| B-03 | Classifications NORMAL / SUSPICIOUS / INSUFFICIENT | `engine.analyze_incident` | `test_engine` | TECHNICAL_OVERVIEW | **Complete** |
| B-04 | Chronology + 30m burst + long-horizon | `engine.py` | window/chrono tests | TECHNICAL_OVERVIEW | **Complete** |
| B-05 | Contextual known-IP fail→success; unfamiliar alone insufficient | `engine.py` | engine tests | TECHNICAL_OVERVIEW | **Complete** |
| B-06 | No double-count; cap 100; no Finance score bonus | `engine.py` (incl. RULE-003 failure-set dedupe) | overlap + multi-success + independent-pattern tests | TECHNICAL_OVERVIEW / ADR-007 | **Complete** (B3 fix) |
| B-07 | Severity / priority separate; no LOW for normals | `engine.py` | severity/classification tests | DATA_MODEL | **Complete** |
| B-08 | Policy TF-IDF retrieval | `retrieval.py` | retrieval tests (need sklearn) | — | **Complete** (env may skip) |
| B-09 | AI grounded + citation validation + no fabricate | `ai_client.py` grounded prompt + claim guards | `test_ai_client` | ADR-004 | **Complete** (B3) |
| B-10 | Stale report / one decision per report | `workflow.py` + `audit_store` unique `report_id` | `test_workflow`, `test_audit_store` | — | **Complete** (B1) |
| B-11 | **SQLite audit across restart** | `audit_store.py`; `app` hydrate/save | `test_audit_store` | ADR-006 superseded | **Complete** (B1) |
| B-12 | Audit fields: decision, incident/report, evidence, policies, timestamp; no secrets | `workflow.build_decision_record` + `audit_store` | `test_audit_store` | DATA_MODEL | **Complete** (B1) |
| B-13 | Dataset covers scenario classes | `data/incidents.json` (13) + `tests/fixtures/` | `test_scenario_fixtures`, `test_engine` | `SCENARIO_COVERAGE_MATRIX.md` | **Complete** (B2) |
| B-14 | Policy schema conditions/categories | enriched `policies.json`; optional-safe loader/retrieval | `test_retrieval`, `test_data_loader` | DATA_MODEL | **Complete** (B3) |

## Proposed backend phases

| Phase | Goal | Files | Depends |
| --- | --- | --- | --- |
| **B1** | SQLite audit store + enriched decision records + ADR/req/doc sync; stdlib `sqlite3` only | `audit_store.py`, `workflow.py`, minimal `app.py` persist hook, `tests/test_audit_store.py`, `.gitignore`, DECISIONS/REQUIREMENTS/AGENTS/DATA_MODEL/TECHNICAL_OVERVIEW | **Implemented this turn** — await approval before B2 |
| **B2** | Expand synthetic scenarios via fixtures (keep production JSON compatible); optional production dataset growth without UI metadata | `tests/fixtures/…`, `data/incidents.json`, `test_scenario_fixtures.py`, `docs/SCENARIO_COVERAGE_MATRIX.md` | **Implemented** — await approval before B3 |
| **B3** | AI grounding + claim guards; policy enrichment; RULE-003 duplicate-score fix | `ai_client.py`, `engine.py`, `retrieval.py`, `data_loader.py`, `data/policies.json`, tests, ADRs | **Implemented** — await approval before B4 |
| **B4** | Document/stabilize partition-load contract; wire app to process valid + report invalid | `data_loader.py`, `app.py` (minimal), tests, `VALIDATION_CONTRACT.md` | **Implemented** |
| **B5** | Final static + dynamic backend audit | compile/import review, full unittest, runtime integration harness | **Passed** (see agent B5 report); `TESTING_AND_SUBMISSION.md` now documents SQLite restart verification |

**UI (`app.py` presentation, filters):** owned by other member — backend will only add a minimal persistence call path where decisions are already recorded.
