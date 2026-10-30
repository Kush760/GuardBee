# GuardBee documentation inventory

**Last consistency pass:** CH-07 (documentation vs Scope v2.2 + root implementation)  
**Confirmed source of truth for MVP product scope:** [`MVP_SCOPE_v2.2.md`](MVP_SCOPE_v2.2.md)

**Precedence used**

1. `docs/MVP_SCOPE_v2.2.md`
2. Explicitly approved change phases (CH-01…CH-06)
3. Current root code/tests as implementation evidence
4. Other docs only when consistent with (1)–(3)

**Resolved conflict:** Scope v2.2 requires SQLite audit persistence. Root implementation uses `audit_store.py` (stdlib SQLite). ADR-006, FR-09/NFR-06, README, and AGENTS now describe SQLite (session state only mirrors the store for UI). Older “session-only audit” wording elsewhere is treated as obsolete and corrected in the CH-07 pass.

| Path | Purpose | Classification | Notes |
| --- | --- | --- | --- |
| `docs/MVP_SCOPE_v2.2.md` | Approved MVP scope v2.2 | **Authoritative** | Keep |
| `AGENTS.md` | Agent/module safety rules | Current | Includes `audit_store.py` / SQLite |
| `README.md` | Entry + setup | Current (CH-06) | Keep |
| `GEMINI.md` | Pointer to AGENTS/docs | Current | Keep |
| `docs/ARCHITECTURE.md` | Module map | Current | SQLite hydrate documented |
| `docs/DATA_MODEL.md` | Schema + analysis + audit | Current | Keep |
| `docs/TECHNICAL_OVERVIEW.md` | Rules + contracts | Current | ≥3 burst/sequence; SQLite |
| `docs/DEMO_GUIDE.md` | Demo script | Current | SQLite restart callout |
| `docs/MVP_WORKFLOW.md` | Analyst workflow | Current | Keep |
| `docs/API_DESIGN.md` | Nebius client contract | Current | Keep |
| `docs/SECURITY.md` | Secrets/synthetic safety | Current | Keep |
| `docs/DECISIONS.md` | ADRs | Current | ADR-006 SQLite; ADR-010 INC-1014 Option B |
| `docs/REQUIREMENTS.md` | FR/NFR table | Current | FR-09/NFR-06 SQLite |
| `docs/SCENARIO_COVERAGE_MATRIX.md` | Scenario expectations | Current | INC-1014 Option B |
| `docs/VALIDATION_CONTRACT.md` | Loader partition contract | Current | Keep |
| `docs/BACKEND_REQUIREMENT_MATRIX.md` | Backend checklist | Current | Keep |
| `docs/SRS.md` | SRS | Supporting | Aligned to SQLite in CH-07 |
| `docs/PROJECT_CHARTER.md` | Charter | Supporting | Aligned in CH-07 |
| `docs/PROJECT_FOUNDATION.md` | Foundation | Supporting | Aligned in CH-07 |
| `docs/PROJECT_PLAN.md` | Plan | Supporting | Historical plan; not MVP SoT |
| `docs/ROADMAP.md` | Post-hackathon ideas | Future (not MVP) | MVP SQLite noted; production store still future |
| `docs/ACCEPTANCE_CRITERIA.md` | DoD checklist | Supporting | Test count aligned in CH-07 |
| `docs/TEST_PLAN.md` | Test plan | Supporting | May lag method names; suite is `unittest discover` |
| `docs/TESTING.md` | Test record | Supporting | Refreshed for 80-test root suite |
| `docs/TESTING_AND_SUBMISSION.md` | Submission checks | Current (CH-06) | Keep |
| `docs/DEPLOYMENT.md` | Deploy notes | Supporting | Keep |
| `docs/HANDOFF.md` | Handoff | Supporting | Refreshed in CH-07 |
| `docs/CHANGELOG.md` | Changelog | Supporting | Appended MVP SQLite / v2.2 notes |
| `docs/CONTRIBUTING.md` | Contrib process | Supporting | Keep |
| `docs/BRANCH_PLAN.md` | Team branches | Process | Keep |
| `docs/TASKS.md` | Workstream tasks | Process | Keep |
| `docs/TEAM_ROLES.md` | Roles | Process | Keep |
| `docs/shareable/*.html` | Print handoffs | May lag Markdown | Refresh separately if needed |
| `docs/diagrams/*.mmd` | Mermaid sources | Current | Keep |
| `GUARDBEE_MVP_V2.2_AUDIT_REPORT.md` | Recovery audit (historical) | Evidence | Preserve; not rewritten as live SoT |
| Nested `GuardBee_MVP_v2.2_recovered/` docs | Recovery snapshot | Recovery | May lag root after CH-02/03/06/07 |

Historical recovery ZIPs/backups are preserved outside this inventory’s “archive” actions.
