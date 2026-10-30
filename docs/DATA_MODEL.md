# Data Model (MVP v2.2)

## Incident JSON (`data/incidents.json`)

Root: non-empty JSON **array**.

### Incident object (required)

| Field | Type | Notes |
|---|---|---|
| `id` | non-empty string | Unique across file |
| `title` | non-empty string | |
| `account` | non-empty string | Synthetic account label |
| `department` | non-empty string | |
| `known_ips` | array of non-empty strings | Baseline familiar addresses |
| `events` | non-empty array | See below |

### Optional incident enrichment (used by engine/UI when present)

| Field | Usage |
|---|---|
| `home_country` / `home_city` | Home context for country rules and display |

### Event object (required fields)

| Field | Type | Notes |
|---|---|---|
| `id` | non-empty string | Unique within incident; cited as EVT-* |
| `time_utc` | ISO-8601 string | Parsed with `Z` → UTC |
| `type` | `login_failed` or `login_success` | |
| `ip` | non-empty string | Empty IP is invalid |
| `country` | non-empty string | |

Optional display fields such as `city` may appear; validation does not require them.

## Policy JSON (`data/policies.json`)

Root: non-empty array. Unique `id` values.

| Field | Required | Notes |
|---|---|---|
| `id` | yes | Cited as POL-* |
| `title` | yes | Included in TF-IDF corpus |
| `text` | yes | Included in TF-IDF corpus |
| `description` | no | Validated if present; **not** in current retrieval corpus |
| `categories` | no | Array of non-empty strings if present |
| `conditions` | no | Non-empty string if present |
| `investigation_guidance` | no | Shown in UI when present |

Retrieval return objects add `match_score` (float).

## Analysis output (`analyze_incident`)

| Field | Meaning |
|---|---|
| `risk_score` | int 0–100 |
| `severity` | CRITICAL/HIGH/MEDIUM/LOW or `None` |
| `classification` | NORMAL / SUSPICIOUS / INSUFFICIENT_EVIDENCE |
| `investigation_priority` | NONE / LOW / MEDIUM / HIGH |
| `rule_hits` | list of `{rule_id, flag, points, evidence_ids}` |
| `flags` | human-readable flag strings |
| `evidence_ids` | deduped event ids from hits |
| `suggested_action` | simulated recommendation text |

## Decision record (`build_decision_record`)

| Field | Notes |
|---|---|
| `time_utc` | ISO timestamp |
| `incident_id` | |
| `actor` | default `demo-analyst` |
| `decision` | APPROVED / REJECTED |
| `outcome` | human-readable simulation text |
| `simulation_only` | always True for UI path |
| `report_id` | ties to validated report |
| `report_context_id` | fingerprint |
| `evidence_ids` / `policy_ids` | lists |
| `status` | `RECORDED` |

## SQLite schema (`audit_store.py` only)

Table `audit_decisions`: columns mirroring the decision record (`evidence_ids` / `policy_ids` stored as JSON text; `simulation_only` as integer; unique `report_id`). Used when callers invoke `save_decision` / `list_decisions`; **current `app.py` does not**.

## Validation boundaries

See [VALIDATION_CONTRACT.md](VALIDATION_CONTRACT.md). File-level failures and (for `load_incidents`) any per-record issue abort loading in the UI.
