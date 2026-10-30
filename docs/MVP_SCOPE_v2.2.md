# GuardBee MVP Scope v2.2

## Objectives

Demonstrate an evidence-first investigation workflow for **synthetic** suspicious-login incidents: deterministic risk and evidence first, then local policy context, optional AI explanation, then a human simulated decision.

## Included

- Streamlit console with Dashboard, Security Incidents, and Audit History
- Validated synthetic JSON incidents and policies under `data/`
- Deterministic analysis in `engine.py` (NORMAL / SUSPICIOUS / INSUFFICIENT_EVIDENCE)
- Local TF-IDF policy retrieval (`retrieval.py`)
- Optional Nebius Token Factory reports with citation-ID validation (`ai_client.py`)
- Context fingerprinting and one simulated decision per validated report (`workflow.py`)
- Session-scoped audit list in the UI
- Offline unit tests and GitHub Actions CI (install, JSON load, unittest)

## Excluded

- Live SIEM/SOAR or real IdP/auth integration
- Real account lock, session revoke, or password reset
- Production audit compliance archives
- Fabricated AI responses when the provider fails
- Automatic remediation

## User workflow

1. Load validated synthetic data (fail-closed in the UI).
2. Review dashboard counts driven by `analyze_incident`.
3. Open an incident: timeline, rule hits/evidence, retrieved policies.
4. Optionally request an AI report; keep it only if citations validate.
5. Approve or Reject the simulated recommendation when the gate allows.
6. Inspect session audit history.

## Technical boundaries

| Concern | Boundary |
|---|---|
| Risk truth | `engine.py` only; AI must not override classification |
| Policies | Local JSON + TF-IDF; default min similarity `0.08`, top_k `3` |
| AI | Live provider only; errors surface; no substitute report |
| Decisions | `APPROVED` / `REJECTED`, `simulation_only=True` |
| Audit UI | `st.session_state.audit` only |
| SQLite | Implemented in `audit_store.py`; **not** called by current `app.py` |
| Incident load UI | `load_incidents` (all-or-nothing); partitioned API unused by UI |

## Known limitations

- Synthetic scenarios only; scores estimate risk, not compromise proof.
- Citation validation ≠ semantic correctness of every AI sentence.
- Session audit disappears on restart.
- Product version remains **MVP v2.2** even when engine comments mention newer scoring experiments.
