# Team Tasks

## Completed and verified in the repository

- Deterministic risk scoring, TF-IDF policy retrieval, schema validation, citation gate, one-decision lock, and SQLite-backed simulation-only audit workflow are implemented.
- The repository has 25 unit tests covering its current pure-Python behavior. Run the verification command in `TESTING.md` in the assigned environment before relying on it.

## In progress / external verification

- Live Nebius account key, model availability, and provider response validation.
- Browser-level Streamlit verification, screenshots, deployment, video, and submission artifacts.

## Pending team tasks

### Workstream B - UI and Frontend Polish

1. **Owner Role & Assigned Branch Name:** `[Member-UI]` on `feature/ui-polish`.
2. **Task Objective & Exact Scope:** Improve layout readability, severity/risk presentation, labels, and approved synthetic-data screenshots without changing business behavior.
3. **Allowed Files to Modify:** `app.py`, `.streamlit/config.toml`, `docs/DEMO_GUIDE.md`, and screenshot assets created under `docs/` if needed.
4. **Prohibited Files (Changes to Avoid):** `engine.py`, `workflow.py`, `ai_client.py`, data contracts, real secrets, and CI provider behavior.
5. **Required Inputs & Expected Outputs:** Existing Streamlit views; deliver a clear dashboard and synthetic-only screenshots.
6. **Dependencies & Interfaces with Other Modules/Team Members:** Coordinate labels with Workstream A; do not break rendered fields used by Workstreams D/E.
7. **Acceptance Criteria:** All existing views remain available, safe-state messaging remains visible, and no real data appears.
8. **Required Automated/Manual Tests:** Run unit suite; manually inspect representative NORMAL / SUSPICIOUS / INSUFFICIENT incidents and disabled/locked controls.
9. **Commit & Pull Request Instructions:** Use small descriptive commits; open a PR to `main` for Workstream A review; do not self-merge.
10. **Proof of Completion Required in PR:** Before/after screenshots, test output, changed-file list, and statement that no secret/data files were added.

### Workstream C - Data Science and Synthetic Incidents

1. **Owner Role & Assigned Branch Name:** `[Member-Data-1]` on `feature/incident-data`.
2. **Task Objective & Exact Scope:** Propose additional synthetic incidents and edge cases while preserving valid JSON and deterministic rule expectations.
3. **Allowed Files to Modify:** `data/incidents.json`, `data/policies.json` only when needed, corresponding tests, and data documentation.
4. **Prohibited Files (Changes to Avoid):** Provider configuration, secrets, production data, automatic action logic, and unreviewed scoring changes.
5. **Required Inputs & Expected Outputs:** Valid synthetic `INC-*`, `EVT-*`, and optional `POL-*` records; expected score/severity assertions.
6. **Dependencies & Interfaces with Other Modules/Team Members:** Coordinate with Workstream A on rule intent and Workstream D on retrievable policy terminology.
7. **Acceptance Criteria:** `data_loader.py` accepts the data; no duplicate IDs; only synthetic/documentation IPs; tests describe expected outcomes.
8. **Required Automated/Manual Tests:** Run full suite and manually inspect new records in Streamlit.
9. **Commit & Pull Request Instructions:** Keep data and tests in one reviewable PR; request Workstream A review.
10. **Proof of Completion Required in PR:** JSON validation output, relevant test names/results, and a note that no personal or production data was used.

### Workstream D - AI/ML, Policy Retrieval and Nemotron

1. **Owner Role & Assigned Branch Name:** `[Member-AI-1]` on `feature/policy-and-ai`.
2. **Task Objective & Exact Scope:** Improve sample policy wording/retrieval coverage and, with approved credentials, manually verify an account-available NVIDIA Nemotron model through Nebius.
3. **Allowed Files to Modify:** `data/policies.json`, `retrieval.py`, `ai_client.py`, focused tests, and AI/retrieval documentation.
4. **Prohibited Files (Changes to Avoid):** Secrets, real customer logs, deterministic scoring ownership, automatic containment, and unsupported benchmark claims.
5. **Required Inputs & Expected Outputs:** Synthetic policy terms, tested threshold behavior, and if authorized a private record of actual model availability; no key in PR.
6. **Dependencies & Interfaces with Other Modules/Team Members:** Coordinate with Workstream C for query terms and A for API/behavior review.
7. **Acceptance Criteria:** Retrieval remains TF-IDF, below-threshold results remain blocked, and citation/error gates remain intact. Any live claim includes reproducible, non-secret evidence.
8. **Required Automated/Manual Tests:** Run unit suite; mock provider tests; if authorized, manually test one live report and citation gate.
9. **Commit & Pull Request Instructions:** Separate policy/retrieval changes from any documentation-only provider verification; submit to Workstream A.
10. **Proof of Completion Required in PR:** Test output, sample match/no-match evidence, and confirmation that secrets and raw provider payloads are absent.

### Workstream E - QA, Testing, Demo Video and Submission

1. **Owner Role & Assigned Branch Name:** `[Member-QA-1]` on `feature/qa-and-submission`.
2. **Task Objective & Exact Scope:** Execute manual verification, prepare the under-three-minute demo, draft submission copy, and maintain release readiness documentation.
3. **Allowed Files to Modify:** `docs/`, `README.md`, test files for verified regressions, and non-secret submission assets.
4. **Prohibited Files (Changes to Avoid):** Secrets, live credentials, core business logic without Workstream A agreement, and claims of unverified deployment/API success.
5. **Required Inputs & Expected Outputs:** Current codebase, `TESTING.md`, `DEMO_GUIDE.md`, and actual observed results; deliver checklist, script, and accurate copy.
6. **Dependencies & Interfaces with Other Modules/Team Members:** Obtain manual evidence from B/D and deployment status from A before final claims.
7. **Acceptance Criteria:** Demo follows actual behavior, labels data synthetic/simulated, and distinguishes completed checks from pending external checks.
8. **Required Automated/Manual Tests:** Run suite, browser checklist, and live-provider checklist only when authorized.
9. **Commit & Pull Request Instructions:** Keep docs and submission assets reviewable; request Workstream A sign-off before publication.
10. **Proof of Completion Required in PR:** Test output, checklist status, screenshots/video link if created, and an explicit list of remaining external blockers.
