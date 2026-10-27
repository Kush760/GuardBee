# GuardBee

GuardBee is an evidence-first security decision copilot for one demo use case: investigating synthetic suspicious-login incidents. It combines deterministic Python risk rules, local TF-IDF policy retrieval, an optional live NVIDIA Nemotron analysis through Nebius Token Factory, and a human-only simulated response.

## Table of contents

- [Quick start](#run-locally) and [testing](#test-and-syntax-checks)
- **MVP scope (authoritative):** [MVP Scope v2.2](docs/MVP_SCOPE_v2.2.md)
- [Requirements](docs/REQUIREMENTS.md), [architecture](docs/ARCHITECTURE.md), [MVP workflow](docs/MVP_WORKFLOW.md), [data model](docs/DATA_MODEL.md), [API design](docs/API_DESIGN.md), [decisions](docs/DECISIONS.md), and [security](docs/SECURITY.md)
- [Validation contract](docs/VALIDATION_CONTRACT.md), [scenario coverage](docs/SCENARIO_COVERAGE_MATRIX.md), [backend requirement matrix](docs/BACKEND_REQUIREMENT_MATRIX.md)
- [Tasks](docs/TASKS.md), [contributing](docs/CONTRIBUTING.md), [demo guide](docs/DEMO_GUIDE.md), [deployment](docs/DEPLOYMENT.md), and [testing and submission](docs/TESTING_AND_SUBMISSION.md)
- Mermaid sources: [architecture](docs/diagrams/architecture.mmd), [workflow](docs/diagrams/workflow.mmd), and [data flow](docs/diagrams/data_flow.mmd)

## Workflow

1. Select a synthetic login incident and review its timestamped event timeline.
2. Inspect deterministic classification, risk score, severity (when applicable), rule flags, and supporting `EVT-*` evidence IDs.
3. Retrieve visible sample policy passages and `POL-*` IDs using scikit-learn TF-IDF similarity.
4. Optionally request a live, evidence-grounded NVIDIA Nemotron report via Nebius Token Factory.
5. Unlock Approve/Reject only if the live report cites current incident events and currently retrieved policy IDs.
6. Record one simulated Approve/Reject decision per validated AI report. Decisions persist in local SQLite via `audit_store.py` and survive app restart. A new AI analysis (new report context) is required before another decision on that investigation path. No account, session, password, SIEM, or external system is changed.

## Classifications (deterministic)

`engine.py` assigns one of three classifications from coded rules. A risk score is **not** proof of compromise.

| Classification | Meaning |
| --- | --- |
| `NORMAL` | Expected activity under the coded rules; not listed as suspicious. Severity is unset. |
| `SUSPICIOUS` | Investigation-supported patterns (for example failure burst and/or fail-then-success sequences that meet coded thresholds). Severity `HIGH` / `MEDIUM` / `LOW` applies only here. |
| `INSUFFICIENT_EVIDENCE` | Inconclusive evidence (for example unfamiliar IP success without qualifying supporting failures, incomplete IP context, or long-horizon failures flagged informationally). Not confirmed compromise and not automatic malice from an unfamiliar IP alone. |

Events are evaluated in chronological `time_utc` order. Known IPs are limited offline context, not a guarantee of safety.

## Safety and scope

- All incident records, accounts, and IPs are synthetic. Bundled examples use reserved documentation IP ranges.
- Risk facts come only from deterministic rules; the model does not calculate the score.
- GuardBee never fabricates an AI answer. If the key is missing, the model is unavailable, the request fails, there is no policy match, or citation validation fails, it explains the failure and leaves Approve/Reject disabled.
- Policy passages are reference material for the analyst and untrusted data for the model, not executable instructions.
- Only policy results with TF-IDF cosine similarity of at least `0.08` are shown. For the four-policy demo corpus, this retains the tested login-policy queries while excluding zero/near-zero lexical overlap. The threshold is a function parameter in `retrieval.py`.
- Simulated audit decisions persist in local SQLite (`data/audit.db` by default; override with `GUARDBEE_AUDIT_DB`). Records do not store secrets. They remain simulation-only.

### Not implemented

GuardBee is a hackathon MVP, not production security software. It does **not** include:

- Real identity-provider or account control (no live session revocation, password reset, or account blocking)
- Live SIEM / SOC ticket integration
- Automatic containment or remediation
- A separate backend service, vector database, or multi-user production architecture

## Synthetic data format

`data/incidents.json` and `data/policies.json` must be non-empty JSON arrays.

- **Incidents:** non-empty `id`, `title`, `account`, and `department`; a `known_ips` array of non-empty strings; and at least one event with `id`, ISO-8601 `time_utc`, `type` (`login_failed` or `login_success`), non-empty `ip`, and `country`. IDs are unique per collection; event IDs are unique within an incident.
- **Policies:** non-empty `id`, `title`, and `text`. Optional enrichment fields (`description`, `categories`, `conditions`, `investigation_guidance`) are validated when present.

The bundled production file currently holds **13** valid incidents (`INC-1011` with an empty IP is fixture-only under `tests/fixtures/`). Policies are the **four**-passage sample corpus (`POL-001` … `POL-004`).

`app.py` loads incidents with `load_incidents_partitioned`: valid rows are analyzed; invalid rows are reported as data-quality messages (not security findings). File-level failures (missing file, malformed JSON, empty collection) stop the app with an error. Policies use fail-closed `load_policies`. See [VALIDATION_CONTRACT](docs/VALIDATION_CONTRACT.md) and [DATA_MODEL](docs/DATA_MODEL.md).

## Run locally

Requires Python 3.10+ (CI uses 3.11). From the repository root:

**Linux / macOS**

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
streamlit run app.py
```

**Windows (PowerShell)**

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .streamlit\secrets.toml.example .streamlit\secrets.toml
streamlit run app.py
```

Put a valid Nebius Token Factory key in `.streamlit/secrets.toml` (never commit this file):

```toml
NEBIUS_API_KEY = "your-key"
# Set this to a NVIDIA Nemotron model currently available to your account.
NEBIUS_MODEL = "nvidia/nemotron-3-super-120b-a12b"
```

`NEBIUS_API_KEY` and `NEBIUS_MODEL` may also be environment variables (`ai_client.py` / `app.py`). The default model string is a configurable starting value, not a guarantee of availability; confirm model ID, credits, and access in your Nebius Token Factory catalog before demoing. The client uses the OpenAI-compatible base URL configured in `ai_client.py`. Never commit `.streamlit/secrets.toml` or `.env`.

The UI can start without a key; Analyze fails safely until credentials and an available model are configured.

## Test and syntax checks

CI and the project completion gate use unittest discovery (same command as `.github/workflows/ci.yml`):

```bash
python -m unittest discover -s tests -v
```

Optional: `python -m pytest tests -v` (`pytest` is listed in `requirements.txt`). Prefer targeting `tests/` so a sibling folder such as a local recovery copy is not collected. Tests cover deterministic risk boundaries, data validation (including partition behavior), relevant/no-match TF-IDF behavior, current-context citation gating, mocked provider failures, SQLite audit persistence, and duplicate-decision prevention. A live Nebius call requires a user-provided credential, an available model, network access, and quota, so it is intentionally not exercised by automated tests.

## Project structure

```text
app.py                 Streamlit UI (dashboard, investigation, decision/audit)
engine.py              Explainable deterministic detection rules
retrieval.py           scikit-learn TF-IDF policy retrieval
ai_client.py           Nebius Token Factory client and citation validation
data_loader.py         JSON parsing, schema validation, incident partition
workflow.py            AI-report context fingerprint and one-decision gate
audit_store.py         Stdlib SQLite persistence for simulated decisions
ui_presentation.py     Classification/severity display helpers
data/                  Synthetic incidents, sample policies (audit.db local, gitignored)
tests/                 Unit tests and fixtures/
.streamlit/            UI theme and untracked secrets template
docs/                  Scope, architecture, workflow, and submission docs
.github/workflows/     CI (install deps, validate JSON load, run unittest)
```

## Documentation

- [MVP Scope v2.2](docs/MVP_SCOPE_v2.2.md) — authoritative product scope.
- [Technical overview](docs/TECHNICAL_OVERVIEW.md) — modules, deterministic rules, retrieval, AI gate, and data contract.
- [Scenario coverage](docs/SCENARIO_COVERAGE_MATRIX.md) — fixture expectations vs proposal notes (including INC-1014 Option B).
- [Testing and submission](docs/TESTING_AND_SUBMISSION.md) — automated coverage, manual verification, and release checklist.
- Additional docs are linked in the [table of contents](#table-of-contents).

## Deployment note

For Streamlit Community Cloud, configure `NEBIUS_API_KEY` (and optionally `NEBIUS_MODEL`) in the host's Secrets interface. Do not commit secrets or claim the app is publicly deployed until a deployment has been created and checked from another browser or device.
