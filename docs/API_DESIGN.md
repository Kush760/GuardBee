# Module Interface Design (MVP v2.2)

Internal Python interfaces used by GuardBee. Authority: the named modules on disk.

## `data_loader.py`

- `load_incidents(path) -> list[dict]` — fail-closed.
- `load_policies(path) -> list[dict]` — fail-closed.
- `load_incidents_partitioned(path) -> IncidentPartitionResult` — valid + issues (unused by UI).
- `DataValidationError` — load/validation failures.

## `engine.py`

- `analyze_incident(incident, *, failure_burst_window_minutes=30) -> dict` — see DATA_MODEL analysis fields.

## `retrieval.py`

- `DEFAULT_MIN_SIMILARITY = 0.08`, `DEFAULT_TOP_K = 3`
- `retrieve_policies(query, policies, top_k=3, min_similarity=0.08) -> list[dict]` with `match_score`.

## `ai_client.py`

- `generate_report(api_key, incident, analysis, policies, model=None, base_url=None) -> str`
- `validate_report_citations(report, evidence_ids, policy_ids) -> tuple[bool, str]`
- `extract_citation_ids(report) -> tuple[list[str], list[str]]`
- `configured_base_url()`, `configured_model()`
- `AIReportError`

## `workflow.py`

- `analysis_context_id(incident, analysis, policies) -> str`
- `can_record_decision(report, report_context_id, current_context_id, report_id, existing_decision) -> bool`
- `build_decision_record(...) -> dict | None`

## `audit_store.py` (standalone relative to UI)

- `save_decision(record, path=None) -> dict`
- `list_decisions(path=None) -> list[dict]`
- `get_decision_by_report_id(report_id, path=None) -> dict | None`
- `initialize_database(path=None)`, `default_db_path()`, `AuditStoreError`

## `ui_presentation.py`

Pure helpers for filters/labels; consumed by unit tests. Current `app.py` defines its own presentation helpers.

## `app.py` integration surface

Imports: `ai_client` (report/validate/extract/config), `data_loader` (`DataValidationError`, `load_incidents`, `load_policies`), `engine.analyze_incident`, `retrieval` (`DEFAULT_MIN_SIMILARITY`, `retrieve_policies`), `workflow` (context + decision helpers). Does **not** import `audit_store` or `ui_presentation`.
