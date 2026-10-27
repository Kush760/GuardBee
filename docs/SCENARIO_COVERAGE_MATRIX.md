# Scenario coverage matrix

**Authoritative proposal:** conversation upload `incidents_revised_proposal_84c1.json` (SHA-256 `3ec66eaea8035c1444c10ab68b8d8f03f2f8bf7a6654c57e4dc1243e8c2f16ac`; also retained in the Phase 0.5 preflight backup).
**Production runtime:** `data/incidents.json` (13 valid cores stripped from that proposal in CH-02).
**Engine authority:** `engine.analyze_incident` (expectations verified against actual rule output; proposal `test_metadata` is not authoritative when it conflicts with coded rules).

## Proposal defects

| ID | Issue | Resolution |
| --- | --- | --- |
| INC-1011 | Empty `ip` is **invalid** for `data_loader` production load | Explicit partition issue; **not** in production. Kept as `tests/fixtures/incomplete_ip_incident.json`. Engine returns `INSUFFICIENT_EVIDENCE` on the raw record. |
| INC-1014 | Proposal `test_metadata` originally expected `SUSPICIOUS` | **CH-03 Option B (approved):** keep engine rules unchanged. The authoritative payload has only **two** failures before an unfamiliar-IP success; `GB-RULE-001` / `GB-RULE-003` require **≥3** qualifying failures. Approved expected result remains `INSUFFICIENT_EVIDENCE` via `GB-RULE-002` (score 0). Production events are preserved (no invented third failure; thresholds not lowered). Chronological ordering is independently required and tested (`test_chronology_fixture_ignores_array_order`; stronger 3-failure chronology in `tests/test_engine.py`). |
| All rows | `test_metadata`, `scenario_context`, `evidence_context` are **test-only** | Stripped from production `data/incidents.json`. Expectations live in `tests/fixtures/scenario_expectations.json`. |

No scoring/classification logic was changed to force proposal expectations.

## Coverage

| ID | Scenario | Expected | Rule / evidence rationale | Production | Test |
| --- | --- | --- | --- | --- | --- |
| INC-1001 | Failure burst then unfamiliar success | `SUSPICIOUS` | `GB-RULE-001` + `GB-RULE-003` (unfamiliar) | Yes | `test_scenario_fixtures` + existing engine tests |
| INC-1002 | Unfamiliar success alone | `INSUFFICIENT_EVIDENCE` | `GB-RULE-002` (0 pts) | Yes | same |
| INC-1003 | One known-IP fail then success | `NORMAL` | Below burst / sequence thresholds | Yes | same |
| INC-1004 | Repeated known-IP successes | `NORMAL` | No failure / unfamiliar rules | Yes | same |
| INC-1005 | Two known-IP fails then successes | `NORMAL` | Two failures &lt; burst threshold | Yes | same |
| INC-1006 | Three known-IP fails then successes | `SUSPICIOUS` | `GB-RULE-001` + `GB-RULE-003` (known IP not auto-safe) | Yes | same |
| INC-1007 | Known successes + one unfamiliar success | `INSUFFICIENT_EVIDENCE` | `GB-RULE-002` | Yes | same |
| INC-1008 | Burst then unfamiliar successes | `SUSPICIOUS` | `GB-RULE-001` + `GB-RULE-003` | Yes | same |
| INC-1009 | Failures outside 30m window | `INSUFFICIENT_EVIDENCE` | `GB-RULE-006` (0 pts) | Yes | same |
| INC-1010 | Overlapping rule evidence | `SUSPICIOUS` | Shared failures scored once via `GB-RULE-001`; `GB-RULE-003` once per failure set; score ≤100 | Yes | `test_overlapping_evidence_does_not_exceed_cap` |
| INC-1011 | Missing / empty IP | `INSUFFICIENT_EVIDENCE` | Loader reject; engine incomplete-context path | No | `test_incomplete_ip_loader_and_engine` |
| INC-1012 | Known-IP burst then success | `SUSPICIOUS` | Known IP is context only | Yes | same |
| INC-1013 | Same pattern, Finance dept | `SUSPICIOUS` | Score parity with INC-1012; no department bonus | Yes | `test_department_independent_scoring_parity` |
| INC-1014 | Out-of-order timestamps | `INSUFFICIENT_EVIDENCE` | Timestamp sort applied; two failures &lt; RULE-001/003 threshold → `GB-RULE-002` (CH-03 Option B) | Yes | `test_chronology_fixture_ignores_array_order` |

## Files

- Production runtime: `data/incidents.json` (13 valid incidents; no test metadata)
- Authoritative proposal: verified upload / Phase 0.5 backup copy of `incidents_revised_proposal_84c1.json`
- Fixtures: `tests/fixtures/scenario_incidents.json`, `scenario_expectations.json`, `incomplete_ip_incident.json`
- Tests: `tests/test_scenario_fixtures.py` (existing `tests/test_engine.py` synthetic cases retained)
