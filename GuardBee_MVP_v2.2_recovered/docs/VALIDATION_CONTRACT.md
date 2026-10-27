# Incident validation and partition-load contract

**Source of truth:** `docs/MVP_SCOPE_v2.2.md` §1.2 / §4  
**Implementation:** `data_loader.py`  
**Primary consumer:** `app.py` (loads incidents for analysis)

## APIs

| API | Behavior |
| --- | --- |
| `partition_incidents(value)` | Partitions an in-memory JSON array into valid incidents and explicit issues. |
| `load_incidents_partitioned(path)` | Reads a file, then partitions. |
| `validate_incidents(value)` | Fail-closed: any issue raises `DataValidationError`. |
| `load_incidents(path)` | Fail-closed file load using `validate_incidents`. |

## Result type

`IncidentPartitionResult`:

- `valid`: list of schema-valid incident dicts (safe for `engine.analyze_incident`)
- `issues`: list of `IncidentValidationIssue(index, message, incident_id | None)`
- `errors`: derived list of human-readable strings (`issue.as_text()`)
- Unpacks as `(valid, errors)` for compatibility

Every rejected record produces exactly one issue. Records are never silently dropped.

## File-level hard failures (`DataValidationError`)

These are **not** per-record issues:

| Input | Result |
| --- | --- |
| Missing / unreadable file | `DataValidationError` (“Could not read…”) |
| Malformed JSON | `DataValidationError` (“not valid JSON”) |
| Root not a non-empty array | `DataValidationError` (“non-empty JSON array”) |

## Per-record issues (partition path)

Reported with array index and `incident_id` when available:

- Missing/invalid required incident fields (`id`, `title`, `account`, `department`)
- Invalid `known_ips`
- Empty/missing events; invalid event fields
- Invalid event `type` (must be `login_failed` / `login_success`)
- Invalid `time_utc`
- Empty/missing event `ip` (must not be treated as unfamiliar)
- Duplicate event IDs within an incident
- Duplicate incident IDs (first kept; later duplicates reported)

## Consumer rules

1. Call `load_incidents_partitioned` (or `partition_incidents`) when partial processing is allowed.
2. Surface `result.errors` / `result.issues` as **data-quality / validation** messages — never as NORMAL/SUSPICIOUS security findings.
3. Pass **only** `result.valid` to `analyze_incident`.
4. If `valid` is empty after partition, stop analysis and require data repair.
5. Callers that need all-or-nothing semantics must keep using `load_incidents` / `validate_incidents`.

## UI integration note

`app.py` already uses `load_incidents_partitioned`, shows validation captions for excluded records, and analyzes only `valid` incidents. Further presentation polish (dedicated Audit/Validation panels) remains UI-owned.
