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

IDs are strings and unique per collection; event IDs are unique within an incident. Event type is `login_failed` or `login_success`, and timestamps must be ISO-8601. The bundled examples use RFC 5737 documentation ranges such as `198.51.100.x` and `203.0.113.x`. The validator does not enforce an IP-range restriction, so any future data contributor must preserve the synthetic-data policy.

## Policy collection

`data/policies.json` is a non-empty array. Each `POL-*` record has a unique non-empty `id`, `title`, and `text`. `retrieval.py` adds a transient `match_score` only to in-memory retrieved records.

## Deterministic assessment output

`analyze_incident` returns `risk_score`, `severity`, `rule_hits`, `flags`, `evidence_ids`, and `suggested_action`. Each rule hit includes `rule_id`, text flag, point value, and its direct evidence IDs.

## Session audit record

An approved or rejected simulation creates an in-memory record with `time_utc`, `incident_id`, `actor` (`demo-analyst`), `decision`, `outcome`, `simulation_only`, and `report_id`. It is not written to a database or file.
