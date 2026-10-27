# Testing Record

## Recorded automated result

The current codebase contains 25 `unittest` test methods. The recorded local verification command is:

```powershell
E:\Hackathon\sentinel-beginner-starter\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Recorded result: **25 tests passed**. The test time is environment-dependent; do not reuse an old duration as a new result without rerunning the command.

## Test inventory

### `TestReportValidation` (8)

- `test_accepts_report_with_supplied_event_and_policy_citations`
- `test_rejects_fabricated_or_stale_event_ids`
- `test_rejects_policy_that_was_not_retrieved`
- `test_rejects_missing_policy_or_event_citation`
- `test_rejects_uncited_report`
- `test_missing_key_is_a_safe_error`
- `test_provider_failure_is_a_safe_error`
- `test_empty_or_malformed_provider_response_is_a_safe_error`

### `TestDataValidation` (6)

- `test_existing_incident_data_is_valid`
- `test_missing_required_incident_field_is_rejected`
- `test_invalid_event_type_and_empty_policy_data_are_rejected`
- `test_malformed_json_is_rejected`
- `test_missing_file_is_rejected`
- `test_policy_requires_text`

### `TestGuardBeeRulesAndRetrieval` (7)

- `test_high_risk_login_has_explainable_evidence`
- `test_known_ip_case_is_low_risk`
- `test_unfamiliar_success_is_medium_risk`
- `test_three_failures_reach_medium_boundary`
- `test_tfidf_returns_ranked_policy_records`
- `test_tfidf_returns_no_match_for_unrelated_or_empty_query`
- `test_tfidf_threshold_can_exclude_weak_matches`

### `TestDecisionWorkflow` (4)

- `test_approve_blocks_duplicate_and_conflicting_decision`
- `test_reject_and_new_analysis_are_allowed_once_each`
- `test_stale_report_context_cannot_authorize_decision`
- `test_context_changes_when_retrieved_policy_changes`

## Manual checks pending authorized configuration

- Streamlit browser startup and all tabs with the current data.
- Missing-key and no-policy-match UI messages.
- One real Nebius/Nemotron request with a permitted key/account/model.
- Report citation display and decision enablement after that response.
- Simulation-only outcome, one-decision lock, and temporary-audit reset behavior.
- Deployment from `main` and access from another browser/device.
