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

## ADR-004: Citation gate and unsupported-claim guardrails

**Decision:** Require current `EVT-*` and retrieved `POL-*` IDs before enabling a decision, and reject reports that claim confirmed compromise (or treat unfamiliar IP alone as proof of malice). Prompt grounding must include deterministic classification, score, severity, priority, rules, and evidence.  
**Why:** It prevents a citation-free, stale, fabricated, or over-certain report from authorizing a simulation.  
**Consequence:** Membership and lightweight certainty checks are necessary guardrails, not full semantic fact-checking.

## ADR-007: Deduplicate GB-RULE-003 by shared failure evidence

**Decision:** Score at most one `GB-RULE-003` contribution per distinct failure-evidence set; additional successes that reuse the same prior failures append evidence IDs without adding points. Distinct failure sets (independent patterns) may each contribute.  
**Why:** MVP Scope v2.2 §3 forbids repeatedly counting the same underlying evidence while still allowing independent signals.  
**Consequence:** One burst followed by many successes no longer inflates the score; multi-IP independent bursts can still stack up to the cap of 100.

## ADR-005: One decision per report

**Decision:** Bind one decision to a context-fingerprinted report ID.  
**Why:** Avoid duplicate or conflicting simulations during Streamlit reruns.  
**Consequence:** Reanalysis is required for another decision.

## ADR-006: Simulated decisions with SQLite audit (supersedes session-only)

**Decision:** Persist simulated Approve/Reject decisions in a local SQLite file via stdlib `sqlite3` (`audit_store.py`). Session state still mirrors the store for the active UI.  
**Why:** MVP Scope v2.2 §6 / §1.11 require audit history across app restart while remaining simulation-only (no real account control).  
**Consequence:** One row per `report_id`; records hold incident/report references, decision, timestamp, evidence/policy IDs, and status—never secrets. Default path is `data/audit.db` (gitignored); override with `GUARDBEE_AUDIT_DB`. Earlier “session-only audit” language in older docs is obsolete for this requirement.

## ADR-008: Single-page UI for MVP Scope v2.2 §7

**Decision:** Keep one Streamlit entry (`app.py`) that covers Dashboard, Security Incidents, and Audit History as in-page regions (metrics/filters, Investigate/Policy tabs, Decision & audit tab). Do **not** add `pages/` multipage navigation for the MVP.  
**Why:** §7 asks to improve those workflow areas and to distinguish classifications and evidence; it does not mandate separate Streamlit routes. ADR-001 already chose a single inspectable app.  
**Consequence:** Demo and docs refer to the three areas as workflow sections of one composition. Multipage navigation would need an explicit scope change.

## ADR-009: Severity LOW band and investigation priority (no unapproved recalibration)

**Decision:** Retain the coded severity thresholds (HIGH ≥ 70, MEDIUM 30–69, LOW &lt; 30 for `SUSPICIOUS` only) and map `investigation_priority` from classification and severity. Do **not** change rule point values or add department/asset score or priority bonuses without an approved requirement plus regression tests.  
**Why:** Scope §3 lists the LOW band as a baseline to retain and test, and allows calibration only when evidence supports a change. Current positive rule points for suspicious patterns are 25–40 (and bursts add 30), so representative `SUSPICIOUS` cases land in MEDIUM or HIGH; LOW remains implemented for scores below 30. Scope mentions asset criticality as a priority consideration; the MVP shows `department` as analyst context and deliberately removed Finance score inflation, so priority stays classification/severity-derived.  
**Consequence:** Docs and demos must not claim that every severity band appears in the current corpus. Changing points or adding criticality weighting is out of band until explicitly approved.
