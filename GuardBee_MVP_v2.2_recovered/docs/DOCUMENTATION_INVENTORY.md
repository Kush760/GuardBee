# GuardBee documentation inventory

**Audit date:** 2026-10-26 (local working tree)  
**Confirmed source of truth for MVP product scope:** [`MVP_SCOPE_v2.2.md`](MVP_SCOPE_v2.2.md) (copied into the repo from the approved conversation scope; version text: MVP scope reference v2.2).

**Precedence used**

1. `docs/MVP_SCOPE_v2.2.md`
2. Explicitly approved phase instructions (current UI-integration task)
3. Phase roadmap implied by scope + prior approved Phase 1 engine/loader work
4. Current local code/tests as implementation evidence
5. Other docs only when consistent with (1)

**Open conflict (does not block UI-only work):** Scope v2.2 requires SQLite audit persistence. `docs/DECISIONS.md` ADR-006, `docs/REQUIREMENTS.md` FR-09/NFR-06, and `AGENTS.md` still describe session-only audit / no database without approval. Those files were **not** archived. Persistence remains out of scope for the current UI phase.

| Path | Purpose | Classification | Conflict | Recommended action |
| --- | --- | --- | --- | --- |
| `docs/MVP_SCOPE_v2.2.md` | Approved MVP scope v2.2 | **Authoritative** | — | Keep; do not archive |
| `AGENTS.md` | Agent/module safety rules | Current/supporting (partially stale on DB) | Conflicts with scope SQLite | Leave; update when SQLite phase approved |
| `README.md` | Entry + links | Current/supporting | Links older FR language indirectly | Keep; add scope link |
| `GEMINI.md` | Pointer to AGENTS/docs | Current/supporting | — | Keep |
| `docs/ARCHITECTURE.md` | Module map | Current/supporting (updated Phase 1) | — | Keep |
| `docs/DATA_MODEL.md` | Schema + analysis contract | Current/supporting (updated Phase 1) | — | Keep |
| `docs/TECHNICAL_OVERVIEW.md` | Rules + contracts | Current/supporting (updated Phase 1) | — | Keep |
| `docs/DEMO_GUIDE.md` | Demo script | Current/supporting | — | Keep; refresh for UI filters |
| `docs/MVP_WORKFLOW.md` | Analyst workflow | Current/supporting | Pre-classification UI wording | Keep; light UI update |
| `docs/API_DESIGN.md` | Nebius client contract | Current/supporting | — | Keep |
| `docs/SECURITY.md` | Secrets/synthetic safety | Current/supporting | — | Keep |
| `docs/DECISIONS.md` | ADRs | Current/supporting; ADR-006 outdated vs scope | SQLite vs session | Leave for manual ADR update later |
| `docs/REQUIREMENTS.md` | FR/NFR table | Current/supporting; FR-09/NFR-06 outdated vs scope | SQLite vs session | Leave; update in persistence phase |
| `docs/SRS.md` | SRS | Supporting; session audit claim | Soft conflict | Leave |
| `docs/PROJECT_CHARTER.md` | Charter | Supporting; temporary audit | Soft conflict | Leave |
| `docs/PROJECT_FOUNDATION.md` | Foundation | Supporting | Soft conflict | Leave |
| `docs/PROJECT_PLAN.md` | Plan | Supporting | — | Leave |
| `docs/ROADMAP.md` | Post-hackathon ideas | Supporting / future (explicitly not MVP) | Must not expand MVP | Leave in place; do not treat as MVP auth |
| `docs/ACCEPTANCE_CRITERIA.md` | DoD checklist | Supporting | — | Leave |
| `docs/TEST_PLAN.md` | Test plan | Supporting | Pre-Phase-1 scoring language | Leave |
| `docs/TESTING.md` | Test record | Supporting; may cite old scores/paths | Stale paths/scores | Leave; refresh later |
| `docs/TESTING_AND_SUBMISSION.md` | Submission checks | Supporting | Temporary-audit checklist | Leave |
| `docs/DEPLOYMENT.md` | Deploy notes | Supporting | — | Leave |
| `docs/HANDOFF.md` | Handoff | Supporting | — | Leave |
| `docs/CHANGELOG.md` | Changelog | Supporting; pre-Phase-1 | Incomplete | Leave; append later |
| `docs/CONTRIBUTING.md` | Contrib process | Supporting | — | Leave |
| `docs/BRANCH_PLAN.md` | Team branches | Supporting / process | — | Leave (README-linked) |
| `docs/TASKS.md` | Workstream tasks | Supporting / process | — | Leave |
| `docs/TEAM_ROLES.md` | Roles | Supporting / process | — | Leave |
| `docs/shareable/*.html` | Print handoffs | Duplicate renderings of MD | May lag MD | Leave (README-linked); refresh separately |
| `docs/diagrams/*.mmd` | Mermaid sources | Current/supporting | — | Keep |
| `docs/archive_review/` | Archive holding area | Meta | — | Keep |
| `docs/DOCUMENTATION_INVENTORY.md` | This inventory | Meta | — | Keep |
| *(none in repo)* `*.pdf` | — | N/A | No PDFs found | — |
| Chat upload only (historical) | Prior audit artifacts outside git | Outside repo | — | Optional later import; not moved |

**Phase B result:** zero document moves into `docs/archive_review/` beyond this README, to avoid breaking submission links or discarding still-required materials.
