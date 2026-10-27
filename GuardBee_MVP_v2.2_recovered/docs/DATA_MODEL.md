# Data Model

## Incident collection

`data/incidents.json` is a non-empty array. Each incident contains:

```json
{
  "id": "INC-1001",
  "title": "string",
  "account": "synthetic-account@example.test",
  "department": "string",
  "known_ips": ["203.0.113.10"],
  "events": [
    {
      "id": "EVT-001",
      "time_utc": "2026-10-17T08:00:00Z",
      "type": "login_success",
      "ip": "203.0.113.10",
      "country": "string"
    }
  ]
}
```

IDs are strings and unique per collection; event IDs are unique within an incident. Event type is `login_failed` or `login_success`, and timestamps must be ISO-8601. Event `ip` must be a non-empty string; an empty IP is invalid and must not be interpreted as an unfamiliar address. The bundled examples use RFC 5737 documentation ranges such as `198.51.100.x` and `203.0.113.x`. The validator does not enforce an IP-range restriction, so any future data contributor must preserve the synthetic-data policy.

`validate_incidents` / `load_incidents` remain fail-closed (all-or-nothing). Callers that must process valid rows while reporting invalid ones use `partition_incidents` / `load_incidents_partitioned`, which return `IncidentPartitionResult` (`valid` + structured `issues`) and never silently discard invalid records. `app.py` consumes the partitioned path and analyzes only `valid` incidents. See `docs/VALIDATION_CONTRACT.md`. Expected classifications and other test-only metadata must not be stored in production `data/incidents.json`.

Scenario expectations for MVP coverage live under `tests/fixtures/` (`scenario_incidents.json`, `scenario_expectations.json`, `incomplete_ip_incident.json`). See `docs/SCENARIO_COVERAGE_MATRIX.md`. Extra proposal fields such as `test_metadata`, `scenario_context`, and `evidence_context` are not part of the production schema.

## Policy collection

`data/policies.json` is a non-empty array. Each `POL-*` record requires unique non-empty `id`, `title`, and `text`. Optional MVP enrichment fields (Scope §5) may also be present:

- `description` (string)
- `categories` (array of non-empty strings)
- `conditions` (string)
- `investigation_guidance` (string)

Missing optional fields are allowed; invalid types for present optionals are rejected. `retrieval.py` includes optional fields in TF-IDF search text when present and adds a transient `match_score` only to in-memory retrieved records.

## Deterministic assessment output

`analyze_incident` returns:

- `classification`: `NORMAL`, `SUSPICIOUS`, or `INSUFFICIENT_EVIDENCE`
- `risk_score`: integer 0–100 (capped); not proof of account compromise
- `severity`: `HIGH` / `MEDIUM` / `LOW` only when classification is `SUSPICIOUS`; otherwise `null` (normal activity never receives `LOW` merely for a zero score)
- `investigation_priority`: `NONE` / `LOW` / `MEDIUM` / `HIGH`
- `rule_hits`, `flags`, `evidence_ids`, `suggested_action`

Each rule hit includes `rule_id`, text flag, point value, and its direct evidence IDs. Events are evaluated in chronological timestamp order. Failure bursts use a configurable window (default 30 minutes).

## Simulated audit record (SQLite)

An approved or rejected simulation creates a durable record persisted by `audit_store.py` (default `data/audit.db`, override `GUARDBEE_AUDIT_DB`). Fields:

| Field | Meaning |
| --- | --- |
| `time_utc` | Decision timestamp (ISO-8601 UTC) |
| `incident_id` | Synthetic incident under review |
| `actor` | Demo actor (`demo-analyst`) |
| `decision` | `APPROVED` or `REJECTED` |
| `outcome` | Human-readable simulation outcome text |
| `simulation_only` | Always true for MVP |
| `report_id` | Validated AI report ID (unique; one decision) |
| `report_context_id` | Evidence/policy context fingerprint at decision time |
| `evidence_ids` | Event IDs referenced by the deterministic analysis |
| `policy_ids` | Retrieved policy IDs shown for that analysis |
| `status` | Persistence status (`RECORDED`) |

Secrets (`api_key`, tokens, passwords) must never appear on audit rows. Streamlit session state mirrors the store for display after hydrate on startup.
