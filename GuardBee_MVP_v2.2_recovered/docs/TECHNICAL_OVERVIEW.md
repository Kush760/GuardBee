# GuardBee Technical Overview

## Architecture

GuardBee is one Python Streamlit application. It has no separate backend service, vector database, or real security integration. Simulated audit decisions use local stdlib SQLite (`audit_store.py`).

| Component | Responsibility |
| --- | --- |
| `app.py` | Streamlit UI, safe data-load handling, AI request flow, approval controls, and SQLite audit hydrate/display. |
| `audit_store.py` | Stdlib SQLite persistence for simulated decisions (`GUARDBEE_AUDIT_DB` override). |
| `data_loader.py` | JSON parsing and validation of incident and policy collections. |
| `engine.py` | Explainable deterministic risk scoring and evidence collection. |
| `retrieval.py` | Local scikit-learn TF-IDF policy ranking. |
| `ai_client.py` | OpenAI-compatible Nebius Token Factory request and report-citation validation. |
| `workflow.py` | Analysis-context fingerprint and one-decision-per-report gate. |

## Deterministic risk rules

The rule engine evaluates the selected incident without an AI model. Events are sorted by `time_utc` before sequence checks. Classification (`NORMAL` / `SUSPICIOUS` / `INSUFFICIENT_EVIDENCE`), risk score, severity, and investigation priority are separate fields. A high score is not proof of compromise. Static `known_ips` are limited offline context, not definitive trust.

| Rule | Points | Evidence behavior |
| --- | ---: | --- |
| GB-RULE-001: ≥3 failed logins inside the burst window (default 30 minutes) | 30 | Failure event IDs in the densest in-window cluster. |
| GB-RULE-003: chronological failure burst then success on the same IP | 25 known IP / 40 unfamiliar IP | Prior in-window failures plus success ID(s). One contribution per distinct failure-evidence set; later successes sharing that set append evidence without extra points. Independent failure sets may each contribute. Known IP is not automatic safety. |
| GB-RULE-002: unfamiliar success without supporting failure evidence | 0 | Informational only → `INSUFFICIENT_EVIDENCE`, not automatic suspicion. |
| GB-RULE-006: ≥3 failures with no in-window burst | 0 | Longer-term pattern flag, separate from RULE-001. |

Finance department no longer adds risk points. Overlapping failure evidence is not re-scored by a separate unfamiliar-success bonus when RULE-003 already covers that success. Scores are capped at 100. Severity bands `HIGH` ≥ 70, `MEDIUM` 30–69, and `LOW` &lt; 30 apply only to `SUSPICIOUS` cases; `NORMAL` and `INSUFFICIENT_EVIDENCE` use `severity: null`. With the current point table, a positive suspicious contribution is at least 25–30 points, so representative `SUSPICIOUS` incidents in the corpus are MEDIUM or HIGH; the LOW band remains coded for scores below 30 and is not removed without an approved recalibration (ADR-009). `investigation_priority` is derived from classification and severity; `department` is displayed as asset/context for the analyst and does not alter score or priority.

## Policy retrieval

`retrieval.py` builds a TF-IDF representation from each policy title, text, and optional enrichment fields (`description`, `categories`, `conditions`, `investigation_guidance`), then ranks against an investigation query with cosine similarity. Retrieval does not affect deterministic risk scores. The default minimum score is `0.08`. In the bundled four-policy corpus this retains the tested login-policy matches while avoiding zero and near-zero overlap. The threshold is a function parameter for future corpus tuning.

An empty or below-threshold result is an explicit no-match state. The UI does not label unmatched policies as relevant and disables AI analysis because there is no valid policy context to cite.

## Data contract

Both data files must be non-empty JSON arrays.

- An incident requires non-empty `id`, `title`, `account`, and `department`; a `known_ips` list of non-empty strings; and at least one event.
- An event requires non-empty `id`, `time_utc`, `type`, `ip`, and `country`. Timestamps must be ISO-8601, and type must be `login_failed` or `login_success`.
- A policy requires non-empty `id`, `title`, and `text`; optional `description`, `categories`, `conditions`, and `investigation_guidance` are validated when present.
- Incident IDs, policy IDs, and IDs within each incident's events must be unique.

`data_loader.py` raises a controlled validation error for missing files, malformed JSON, or empty collections (file-level failures). Fail-closed helpers (`validate_incidents` / `load_incidents`) reject the whole collection when any record is invalid. `partition_incidents` / `load_incidents_partitioned` return `IncidentPartitionResult` with valid records plus explicit per-record issues (index, message, optional `incident_id`) and never silently drop invalid rows. `app.py` uses the partitioned loader: validation messages are shown as data-quality errors, and only `valid` incidents are passed to `engine.analyze_incident`. Simulated audit history is persisted in local SQLite via `audit_store.py`.

## Live AI boundary

When enabled by the analyst, `ai_client.py` sends the current synthetic incident, a grounded deterministic analysis payload (classification, risk score, severity, investigation priority, rule hits, evidence), and retrieved policies to the Nebius Token Factory OpenAI-compatible endpoint using the selected NVIDIA Nemotron model. The key is read from Streamlit Secrets or the environment; it is not stored in source control. Provider failures and empty/malformed responses raise `AIReportError`; GuardBee never fabricates a substitute report.

The response must be non-empty and cite at least one ID from the current incident plus at least one ID from the policies retrieved for the current analysis. Citation extraction normalizes common Unicode dashes to ASCII and matches simple `EVT-*` / `POL-*` tokens so model typography (for example non-breaking hyphens or `EVT-002-EVT-005` ranges) does not falsely fail or invent unknown IDs. Unknown, stale, unretrieved, or missing IDs invalidate the report. Reports that claim confirmed compromise, or that treat unfamiliar IP alone as proof of malice, are rejected. These checks are necessary guardrails, not full semantic fact-checking.

## Decision and audit gate

The current incident, deterministic analysis, and retrieved policy IDs form a SHA-256 context fingerprint. A report is accepted only for that context. A successful report receives a session-specific report ID; one simulated approval or rejection may be recorded for it. New analysis creates a new report ID and permits one new decision. Changing the incident clears the active report and decision.

The audit record contains UTC timestamp, incident ID, demo actor, decision, outcome, simulation flag, report ID, report context ID, evidence IDs, policy IDs, and status. It is written to SQLite and mirrored in session state after hydrate; secrets are refused.

## Dependencies and secrets

`requirements.txt` declares the direct runtime dependencies: Streamlit, scikit-learn, and the OpenAI Python SDK. Audit persistence uses the Python standard library `sqlite3` module (no extra package). `.gitignore` excludes `.streamlit/secrets.toml`, `.env`, `*.db`, virtual environments, bytecode, pytest cache, coverage output, and common local-editor artifacts. Use `.streamlit/secrets.toml.example` as a template; do not commit a real secret file.
