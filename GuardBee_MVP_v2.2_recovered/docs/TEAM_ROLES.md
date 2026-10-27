# Team Roles

The team uses five workstreams. Owner names remain role placeholders until the lead assigns contributors. Allocation reflects the supplied skills signal: one Web UI vote, three AI/API/Prompt votes, and two Testing/QA votes.

| Workstream | Owner placeholder | Focus | Skills signal |
| --- | --- | --- | --- |
| A - Lead and Core Integration | `[Member-Lead]` | Governance, engine/workflow integration, CI, review, final merge | Cross-functional |
| B - UI and Frontend Polish | `[Member-UI]` | Streamlit layout, visual hierarchy, badges, screenshots | Web UI (1 vote) |
| C - Data Science and Synthetic Incidents | `[Member-Data-1]` | Synthetic logs and edge-case telemetry | Security/data coordination |
| D - AI/ML, Policy Retrieval and Nemotron | `[Member-AI-1]` | Policy coverage, retrieval tuning, provider/model verification | AI/API/Prompt (3 votes) |
| E - QA, Demo and Submission | `[Member-QA-1]` | Edge-case QA, browser checks, video, Devpost copy | Testing/QA (2 votes) |

## Role boundaries

Only Workstream A merges into `main`. Workstreams B-E use the branches in `BRANCH_PLAN.md`, avoid real data/secrets, and provide evidence in their pull requests. Workstream D may test a live account only with explicit authorization and must not publish any credentials or unverified performance claim.
