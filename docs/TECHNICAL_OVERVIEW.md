# GuardBee Technical Overview

## Architecture

GuardBee is one Python Streamlit application. It has no backend service, database, vector database, or real security integration.

| Component | Responsibility |
| --- | --- |
| `app.py` | Streamlit UI, safe data-load handling, AI request flow, approval controls, and temporary audit display. |
| `data_loader.py` | JSON parsing and validation of incident and policy collections. |
| `engine.py` | Explainable deterministic risk scoring and evidence collection. |
| `retrieval.py` | Local scikit-learn TF-IDF policy ranking. |
| `ai_client.py` | OpenAI-compatible Nebius Token Factory request and report-citation validation. |
| `workflow.py` | Analysis-context fingerprint and one-decision-per-report gate. |

## Deterministic risk rules

The rule engine evaluates the selected incident without an AI model.

| Rule | Points | Evidence behavior |
| --- | ---: | --- |
| At least three failed logins | 30 | Includes failed-event IDs. |
| Successful login from an unfamiliar IP | 40 | Includes unfamiliar successful-event IDs. |
| Failed and successful logins share an unfamiliar IP | 15 | Includes related failed and successful IDs. |
| Any triggered rule on a Finance account | 10 | Priority context only; adds no event ID. |

Scores are capped at 100. Severity is `HIGH` at 70 or above, `MEDIUM` from 30 through 69, and `LOW` below 30. The suggested action is also determined from this score.

## Policy retrieval

`retrieval.py` builds a TF-IDF representation from each policy title and text, then ranks it against an investigation query with cosine similarity. The default minimum score is `0.08`. In the bundled four-policy corpus this retains the tested login-policy matches while avoiding zero and near-zero overlap. The threshold is a function parameter for future corpus tuning.

An empty or below-threshold result is an explicit no-match state. The UI does not label unmatched policies as relevant and disables AI analysis because there is no valid policy context to cite.

## Data contract

Both data files must be non-empty JSON arrays.

- An incident requires non-empty `id`, `title`, `account`, and `department`; a `known_ips` list of non-empty strings; and at least one event.
- An event requires non-empty `id`, `time_utc`, `type`, `ip`, and `country`. Timestamps must be ISO-8601, and type must be `login_failed` or `login_success`.
- A policy requires non-empty `id`, `title`, and `text`.
- Incident IDs, policy IDs, and IDs within each incident's events must be unique.

`data_loader.py` raises a controlled validation error for missing files, malformed JSON, incorrect types, duplicate IDs, or invalid values. `app.py` surfaces an actionable error and stops before analysis or decision controls are available.

## Live AI boundary

When enabled by the analyst, `ai_client.py` sends the current synthetic incident, deterministic analysis, and retrieved policies to the Nebius Token Factory OpenAI-compatible endpoint using the selected NVIDIA Nemotron model. The key is read from Streamlit Secrets or the environment; it is not stored in source control.

The response must be non-empty and cite at least one ID from the current incident plus at least one ID from the policies retrieved for the current analysis. Unknown, stale, unretrieved, or missing IDs invalidate the report. These checks are necessary guardrails, not semantic fact-checking.

## Decision and audit gate

The current incident, deterministic analysis, and retrieved policy IDs form a SHA-256 context fingerprint. A report is accepted only for that context. A successful report receives a session-specific report ID; one simulated approval or rejection may be recorded for it. New analysis creates a new report ID and permits one new decision. Changing the incident clears the active report and decision.

The audit record contains UTC timestamp, incident ID, demo actor, decision, outcome, simulation flag, and report ID. It remains in Streamlit session state only.

## Dependencies and secrets

`requirements.txt` declares the direct runtime dependencies: Streamlit, scikit-learn, and the OpenAI Python SDK. `.gitignore` excludes `.streamlit/secrets.toml`, `.env`, virtual environments, bytecode, pytest cache, coverage output, and common local-editor artifacts. Use `.streamlit/secrets.toml.example` as a template; do not commit a real secret file.
