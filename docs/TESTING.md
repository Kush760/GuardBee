# Testing Record

## Recorded automated result

The current codebase contains 54 `unittest` test methods. The recorded local verification command, run from the repository root in a gitignored virtual environment created from `requirements.txt`, is:

```powershell
.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Recorded result (Workstream D, `feature/policy-and-ai`): **54 tests passed** on Python 3.12.10 with `openai` 1.109.1 and scikit-learn 1.9.1. CI uses Python 3.11, which was not available locally, so the suite has not yet been run on 3.11. The test time is environment-dependent; do not reuse an old duration as a new result without rerunning the command.

All tests are offline. Provider tests use mocks or an in-process `httpx.MockTransport` and never contact Nebius.

## Test inventory

### `TestReportValidation` (15)

- `test_accepts_report_with_supplied_event_and_policy_citations`
- `test_accepts_lowercase_form_of_allowed_ids`
- `test_rejects_fabricated_or_stale_event_ids`
- `test_rejects_lowercase_fabricated_ids`
- `test_rejects_ids_glued_to_letter_or_underscore_prefix`
- `test_rejects_ids_written_with_unicode_dashes`
- `test_unicode_dash_form_of_allowed_id_does_not_count_as_citation`
- `test_rejects_ids_with_trailing_underscore_suffix`
- `test_policy_id_cannot_satisfy_event_requirement`
- `test_rejects_policy_that_was_not_retrieved`
- `test_rejects_missing_policy_or_event_citation`
- `test_rejects_uncited_report`
- `test_missing_key_is_a_safe_error`
- `test_provider_failure_is_a_safe_error`
- `test_empty_or_malformed_provider_response_is_a_safe_error`

### `TestProviderBoundary` (10)

- `test_valid_response_returns_stripped_report`
- `test_request_uses_documented_endpoint_timeout_and_payload`
- `test_model_defaults_to_environment_override`
- `test_timeout_is_a_safe_error`
- `test_connection_failure_is_a_safe_error`
- `test_http_errors_are_safe_and_do_not_leak_key`
- `test_invalid_json_is_a_safe_error`
- `test_non_json_content_type_is_a_safe_error`
- `test_unexpected_response_structures_are_safe_errors`
- `test_missing_or_blank_content_is_a_safe_error`

### `TestPolicyRetrieval` (12)

- `test_documented_defaults`
- `test_bundled_incidents_retrieve_expected_policy_ids`
- `test_does_not_pad_results_with_below_threshold_policies`
- `test_top_k_truncates_ranked_results`
- `test_non_positive_top_k_returns_nothing`
- `test_threshold_is_inclusive`
- `test_whitespace_query_returns_nothing`
- `test_stop_word_only_corpus_and_query_return_nothing`
- `test_equal_scores_keep_corpus_order`
- `test_results_are_deterministic_and_inputs_unchanged`
- `test_invalid_arguments_are_rejected`
- `test_malformed_policy_entries_are_rejected`

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
