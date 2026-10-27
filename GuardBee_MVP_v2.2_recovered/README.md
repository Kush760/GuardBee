# GuardBee

GuardBee is an evidence-first security decision copilot for one demo use case: investigating synthetic suspicious-login incidents. It combines deterministic Python risk rules, local TF-IDF policy retrieval, an optional live NVIDIA Nemotron analysis through Nebius Token Factory, and a human-only simulated response.

## Table of contents

- [Quick start](#run-locally) and [testing](#test-and-syntax-checks)
- **MVP scope (authoritative):** [MVP Scope v2.2](docs/MVP_SCOPE_v2.2.md)
- [Requirements](docs/REQUIREMENTS.md), [architecture](docs/ARCHITECTURE.md), [MVP workflow](docs/MVP_WORKFLOW.md), [data model](docs/DATA_MODEL.md), [API design](docs/API_DESIGN.md), [decisions](docs/DECISIONS.md), and [security](docs/SECURITY.md)
- [Validation contract](docs/VALIDATION_CONTRACT.md), [scenario coverage](docs/SCENARIO_COVERAGE_MATRIX.md), [backend requirement matrix](docs/BACKEND_REQUIREMENT_MATRIX.md)
- [Tasks](docs/TASKS.md), [contributing](docs/CONTRIBUTING.md), [demo guide](docs/DEMO_GUIDE.md), [deployment](docs/DEPLOYMENT.md), and [testing and submission](docs/TESTING_AND_SUBMISSION.md)
- Mermaid sources: [architecture](docs/diagrams/architecture.mmd), [workflow](docs/diagrams/workflow.mmd), and [data flow](docs/diagrams/data_flow.mmd)
- Archived historical / duplicate material (local only): [`unnecessary stuff/`](unnecessary%20stuff/) — charter, foundation, plan, SRS, handoff, shareable HTML, proposal backup, etc.

## Workflow

1. Select a synthetic login incident and review its timestamped event timeline.
2. Inspect deterministic risk score, severity, rule flags, and supporting `EVT-*` evidence IDs.
3. Retrieve visible sample policy passages and `POL-*` IDs using scikit-learn TF-IDF similarity.
4. Request a live, evidence-grounded NVIDIA Nemotron report via Nebius Token Factory.
5. Unlock Approve/Reject only if the live report cites current incident events and currently retrieved policy IDs.
6. Record one in-session simulated decision per AI analysis. Running a new AI analysis permits one new decision; no account, session, password, or external system is changed.

## Safety and scope

- All incident records, accounts, and IPs are synthetic. Reserved documentation IP ranges are used.
- Risk facts come only from deterministic rules; the model does not calculate the score.
- GuardBee never fabricates an AI answer. If the key is missing, model unavailable, or request fails, it explains the failure and leaves approval disabled.
- Policy passages are reference material for the analyst and untrusted data for the model, not executable instructions.
- Only policy results with TF-IDF cosine similarity of at least `0.08` are shown. For the four-passage demo corpus, this is the small minimum that retains the tested login-policy queries while excluding zero/near-zero lexical overlap; the retrieval tests cover matching, threshold exclusion, and no-match behavior. It is configurable for a future policy corpus.
- Simulated audit decisions persist in local SQLite (`audit_store.py`); they remain simulation-only and never change real accounts.

GuardBee is a hackathon MVP, not production security software. It has no real identity-system integration, automatic containment, or claim of compromise detection.

## Synthetic data format

`data/incidents.json` and `data/policies.json` must be non-empty JSON arrays. Incident records require non-empty `id`, `title`, `account`, and `department` strings; a `known_ips` string array; and at least one event with `id`, ISO-8601 `time_utc`, `type` (`login_failed` or `login_success`), `ip`, and `country`. Policy records require non-empty `id`, `title`, and `text` strings. IDs must be unique in their collections.

GuardBee stops safely with an actionable UI error if these checks fail. It does not substitute fallback data or allow an invalid incident to reach analysis, AI, approval, or audit steps.

## Run locally

Requires Python 3.10+.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .streamlit\secrets.toml.example .streamlit\secrets.toml
```

Put a valid Nebius Token Factory key in `.streamlit/secrets.toml`:

```toml
NEBIUS_API_KEY = "your-key"
# Set this to a NVIDIA Nemotron model currently available to your account.
NEBIUS_MODEL = "nvidia/nemotron-3-super-120b-a12b"
```

Then start the app:

```powershell
streamlit run app.py
```

`NEBIUS_API_KEY` and `NEBIUS_MODEL` may also be environment variables. The default model is a configurable starting value, not a guarantee of availability; confirm model ID, credits, and access in your Nebius Token Factory catalog before demoing. Never commit `.streamlit/secrets.toml` or `.env`.

## Test and syntax checks

CI and the project completion gate use unittest discovery (same command as `.github/workflows/ci.yml`):

```powershell
python -m unittest discover -s tests -v
```

Optional: `python -m pytest tests -v` (`pytest` is listed in `requirements.txt`). Prefer targeting `tests/` so a sibling folder such as a local final copy is not collected. Tests cover deterministic risk boundaries, data validation, relevant/no-match TF-IDF behavior, current-context citation gating, mocked provider failures, SQLite audit persistence, and duplicate-decision prevention. A live Nebius call requires a user-provided credential, an available model, network access, and quota, so it is intentionally not exercised by tests.

## Project structure

```text
app.py                 Streamlit dashboard; hydrates/displays SQLite audit
engine.py              Explainable deterministic detection rules
retrieval.py           scikit-learn TF-IDF policy retrieval
ai_client.py           Live Nebius Token Factory / NVIDIA Nemotron client
data_loader.py         JSON parsing and schema validation
workflow.py            AI-report context and one-decision approval gate
audit_store.py         Stdlib SQLite persistence for simulated decisions
data/                  Synthetic incidents and sample company policies
tests/                 Unit tests
.streamlit/            UI theme and untracked secrets template
docs/                  Foundation, technical, and testing/submission docs
```

## Documentation

- [MVP Scope v2.2](docs/MVP_SCOPE_v2.2.md) - authoritative product scope.
- [Technical overview](docs/TECHNICAL_OVERVIEW.md) - modules, deterministic rules, retrieval, AI gate, and data contract.
- [Testing and submission](docs/TESTING_AND_SUBMISSION.md) - automated coverage, manual verification, and release checklist.
- The complete active documentation index is in the [table of contents](#table-of-contents). Historical drafts live under [`unnecessary stuff/`](unnecessary%20stuff/).

## Deployment note

For Streamlit Community Cloud, configure `NEBIUS_API_KEY` (and optionally `NEBIUS_MODEL`) in the host's Secrets interface. Do not commit secrets or claim the app is publicly deployed until a deployment has been created and checked from another browser or device.
