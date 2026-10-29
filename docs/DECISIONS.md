# Architecture Decisions

## ADR-001: Python and Streamlit

**Decision:** Use one Python Streamlit app.  
**Why:** The MVP needs a fast, inspectable dashboard without a separate frontend/backend.  
**Consequence:** UI and session state live in `app.py`; this is not a multi-user production architecture.

## ADR-002: Deterministic risk before AI

**Decision:** Calculate risk in `engine.py` before any optional model request.  
**Why:** Scores, severity, and evidence must be repeatable and explainable.  
**Consequence:** AI explains supplied evidence but does not establish detection facts.

## ADR-003: Local TF-IDF retrieval

**Decision:** Use scikit-learn TF-IDF with `0.08` minimum similarity.  
**Why:** It is lightweight and tested against the bundled policy corpus.  
**Consequence:** No policy match blocks AI analysis rather than presenting arbitrary passages as relevant.

## ADR-004: Citation gate

**Decision:** Require current `EVT-*` and retrieved `POL-*` IDs before enabling a decision.  
**Why:** It prevents a citation-free, stale, or obviously fabricated report from authorizing a simulation.  
**Consequence:** Membership checks are not full semantic fact-checking.

## ADR-005: One decision per report

**Decision:** Bind one decision to a context-fingerprinted report ID.  
**Why:** Avoid duplicate or conflicting simulations during Streamlit reruns.  
**Consequence:** Reanalysis is required for another decision.

## ADR-006: Simulation only

**Decision:** Record only session-state audit entries.  
**Why:** The hackathon scope excludes real account control.  
**Consequence:** Audit history is non-durable and must be described honestly.

## ADR-007: Event-based dynamic scoring (v2.3)

**Decision:** Build the risk score from each incident's events (failure count, burst speed, sign-ins after the failures, unfamiliar IPs, new country, impossible travel, off-hours, known-only sign-ins) instead of fixed amounts per rule, add a CRITICAL severity band, and give events synthetic city/country locations.  
**Why:** With fixed amounts every HIGH incident scored 70 and every MEDIUM one 55, LOW never occurred, and every unfamiliar-IP event was located "Unknown", so scores did not tell incidents apart.  
**Approval:** Requested by the project owner on 30 Oct 2026 ("START IMPLEMENTATION" on `GuardBee_change_instructions.txt`), which approves this change to the protected `engine.py` and `data_loader.py`. The suggested defaults were used for the open decisions: the listed point values, a CRITICAL band, department never affects the score, and 00:00-05:00 UTC as off-hours.  
**Consequence:** Scoring stays deterministic and in `engine.py` (ADR-002); every point is a visible rule hit. Context signals only weigh incidents that are already suspicious. Policy retrieval queries include the new rule flags, so flag wording was chosen to keep each incident's policy matches relevant.
