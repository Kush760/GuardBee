# Technical Overview (MVP v2.2)

Implementation reference: local `engine.py`, `retrieval.py`, `ai_client.py`, `workflow.py`, `audit_store.py`, `data_loader.py`, and `app.py`.

## Deterministic risk engine

`analyze_incident(incident, failure_burst_window_minutes=30)` sorts events chronologically and scores only from event evidence.

Incomplete IP or invalid timestamps → `INSUFFICIENT_EVIDENCE` (score 0).

| Rule ID | Signal (summary) | Scoring notes |
|---|---|---|
| GB-RULE-001 | Failure burst (≥3 in window) | 5 pts/failure, max 30 |
| GB-RULE-007 | Fast burst rate | Up to 10 |
| GB-RULE-003 | ≥3 prior failures then success (same IP, windowed) | Up to 25 |
| GB-RULE-008 | That success from unfamiliar IP | +15 |
| GB-RULE-002 | Unfamiliar success alone | 0 pts; often INSUFFICIENT |
| GB-RULE-006 | Many failures, no dense burst | 0 pts informational |
| GB-RULE-009–013 | Extra unfamiliar IPs, new country, impossible travel, off-hours, known-only dampener | Only when already suspicious |

**Classification:** SUSPICIOUS if burst≥3 or fail-then-success sequence; else INSUFFICIENT if any rule hit; else NORMAL.

**Severity:** CRITICAL/HIGH/MEDIUM/LOW from score bands **only when SUSPICIOUS**; otherwise `None`.

**Priority:** NONE / LOW / MEDIUM / HIGH from classification + severity.

Risk score is capped at 100 and is **not** proof of compromise.

## Policy retrieval

`retrieve_policies(query, policies, top_k=3, min_similarity=0.08)` builds TF-IDF over `title + text`, ranks by cosine similarity, returns copies with `match_score`.

`app.py` query = incident title + department + analysis flags + suggested action.

No match → AI request and decisions stay locked.

## AI integration

`generate_report(api_key, incident, analysis, policies, …)` posts JSON context to Nebius (OpenAI client). Strips `<think>` blocks and normalizes Unicode dashes inside EVT/POL-looking tokens.

`validate_report_citations(report, evidence_ids, policy_ids)` rejects empty reports, malformed IDs, unknown IDs, or reports missing at least one current EVT and one retrieved POL. Success message states ID checks do not prove semantic support.

**Limitations (current `ai_client.py`):**
- Citation membership is **not** semantic proof of every sentence.
- There is **no** post-hoc regex that rejects “confirmed compromise” or classification-overstatement wording; the system prompt instructs the model not to assert confirmed compromise, but a non-compliant model reply can still pass if its EVT/POL IDs are valid.
- Unicode look-alike dashes in IDs are normalized inside `generate_report` before return; `validate_report_citations` still treats un-normalized Unicode-dash tokens as malformed if called on raw text.
- Live Nebius behavior (latency, quota, model availability) is environment-specific and not guaranteed by unit tests.

## Workflow gating

- `analysis_context_id` — SHA-256 over incident, analysis, and retrieved policy IDs.
- `can_record_decision` — requires non-empty report, matching context id, report id, and no prior decision for that report id.
- `build_decision_record` — `APPROVED`/`REJECTED` only; includes `simulation_only`, evidence/policy ids, `status=RECORDED`.

## Audit implementation

| Layer | Behavior |
|---|---|
| UI (`app.py`) | Appends records to `st.session_state.audit`; Audit History reads that list; warns session-only |
| Module (`audit_store.py`) | SQLite table `audit_decisions`; unique `report_id`; refuses secret-like keys; path `data/audit.db` or `GUARDBEE_AUDIT_DB` |

Do not document SQLite as the live UI path unless `app.py` imports and calls `audit_store`.
