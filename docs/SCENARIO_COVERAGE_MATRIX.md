# Scenario Coverage Matrix (MVP v2.2)

Synthetic incidents in local `data/incidents.json` (titles verified from file). **Expected engine outcomes** are not asserted here without re-running tests against the current dirty/protected test suite; mark verification status accordingly.

| Incident | Title | Scenario intent (from title/events shape) | Engine outcome | Verification |
|---|---|---|---|---|
| INC-1001 | Suspicious Finance login after repeated failures | Failures then success pattern | *Requires test-source / live analyze* | Unverified in this doc pass |
| INC-1002 | Unfamiliar login requires review | Unfamiliar success emphasis | *Requires test-source / live analyze* | Unverified |
| INC-1003 | Known-location login with one failed attempt | Light / benign-leaning activity | *Requires test-source / live analyze* | Unverified |
| INC-1004 | Repeated successes from a known IP | Known-IP successes | *Requires test-source / live analyze* | Unverified |
| INC-1005 | Two known-IP failures then success | Short failure then success | *Requires test-source / live analyze* | Unverified |
| INC-1006 | Known-IP failure burst then successes | Burst + success on known IP | *Requires test-source / live analyze* | Unverified |
| INC-1007 | Known successes with one unfamiliar login | Mixed familiarity | *Requires test-source / live analyze* | Unverified |
| INC-1008 | Unfamiliar failure burst then successes | Burst + unfamiliar success | *Requires test-source / live analyze* | Unverified |
| INC-1009 | Failures spaced outside burst window | Sparse failures | *Requires test-source / live analyze* | Unverified |
| INC-1010 | Night-time burst and sign-in from an unfamiliar IP | Off-hours + unfamiliar | *Requires test-source / live analyze* | Unverified |
| INC-1011 | Account takeover with impossible travel | Impossible travel / takeover pattern | SUSPICIOUS (engine on current data) | Verified via local `analyze_incident` + fixture expectation |
| INC-1012 | Known-IP burst then success in Quality Assurance | Burst on known IP | *Requires test-source / live analyze* | Unverified |
| INC-1013 | Slow known-IP failures then success in Finance | Slow burst + success | *Requires test-source / live analyze* | Unverified |
| INC-1014 | Out-of-order timestamps with two prior failures | Chronology / ordering stress | *Requires test-source / live analyze* | Unverified |
| INC-1015 | Slow guessing then sign-in from a new country | New-country context | *Requires test-source / live analyze* | Unverified |
| INC-1016 | Rapid password guessing with no sign-in | Failures without success | *Requires test-source / live analyze* | Unverified |

## Rules available to map (from `engine.py`)

GB-RULE-001, 002, 003, 006, 007, 008, 009, 010, 011, 012, 013.

## Policies in `data/policies.json`

POL-001 … POL-005 (unusual login, Finance protection, analyst approval/audit, evidence handling, spaced failures without sign-in).

## Note

`tests/fixtures/scenario_expectations.json` and `test_scenario_fixtures.py` are the place to confirm expected classifications after an authorized test run. This matrix intentionally does not invent PASS/FAIL outcomes.
