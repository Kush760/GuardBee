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
