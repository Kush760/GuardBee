# Validation Contract (MVP v2.2)

Source: `data_loader.py` as called by `app.py`.

## Input validation

| Loader | Behavior |
|---|---|
| `load_incidents(path)` | Read UTF-8 JSON → `validate_incidents` → **fail-closed** |
| `load_policies(path)` | Read UTF-8 JSON → `validate_policies` → fail-closed |
| `load_incidents_partitioned(path)` | Returns `IncidentPartitionResult(valid, issues)` | **Not used by `app.py`** |

Missing file / unreadable path / invalid JSON → `DataValidationError`.

## Required incident fields

Incident: `id`, `title`, `account`, `department`, `known_ips` (non-empty strings list), `events` (non-empty).

Each event: `id`, `time_utc` (ISO-8601), `type` ∈ {`login_failed`,`login_success`}, `ip`, `country` (all non-empty strings).

## Required policy fields

`id`, `title`, `text` (non-empty strings). Optionals must match documented types when present.

## Type constraints

- Root collections must be non-empty JSON arrays.
- Duplicate incident ids among valid rows: partitioned loader reports and keeps first; fail-closed loader raises.
- Duplicate event ids within an incident → error.
- Duplicate policy ids → error.
- Empty string `ip` is explicitly invalid (must not be treated as an unfamiliar address).
- Optional enrichment such as incident `home_country` / `home_city` or event `city` is **not** type-checked by the current loader when present (including blank strings).

## Duplicate handling

- `validate_incidents` / `load_incidents`: any issue (including duplicates) raises with joined messages.
- `partition_incidents`: invalid or duplicate rows become explicit `IncidentValidationIssue` entries; valid list excludes them.

## Fail-closed UI behavior

`app.py` catches `DataValidationError`, shows an error that data could not load safely, captions the validation message, and calls `st.stop()`. It does **not** partially render valid incidents from a mixed invalid file.

## Error handling elsewhere

- Retrieval argument errors → `TypeError` / `ValueError`.
- AI failures → `AIReportError` with provider-safe messages (no API key echo).
- Audit module failures → `AuditStoreError` (UI path unused).
