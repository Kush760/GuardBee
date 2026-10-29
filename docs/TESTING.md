# Testing Record

## Recorded automated result

The current codebase contains 113 `unittest` test methods. The recorded local verification command, run from the repository root in a gitignored virtual environment created from `requirements.txt`, is:

```powershell
.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Recorded result (`dev` branch, Security Analytics Console UI with the v2.3 dynamic-scoring engine and 16-incident dataset): **113 tests passed** on Python 3.12.10 with `openai` 1.109.1, scikit-learn 1.9.1, and Streamlit 1.66.1. CI uses Python 3.11, which was not available locally, so the suite has not yet been run on 3.11. The UI tests need a working Streamlit install (`streamlit.testing`); an environment with mismatched Streamlit/Starlette versions fails to import them. The test time is environment-dependent; do not reuse an old duration as a new result without rerunning the command.

All tests are offline. Provider tests use mocks or an in-process `httpx.MockTransport` and never contact Nebius. UI tests replace `ai_client.generate_report` with a mock that fails the test if any path tries to reach the provider, even when a local `.streamlit/secrets.toml` exists.

## Test inventory

### `TestGuardBeeUI` (24) — headless Streamlit `AppTest`

Pages are reached through the app's own controls (Dashboard "View All" plus the incident list, Dashboard Recent Incidents "View", decision panel "View in Audit History", Audit History "Open incident"), so navigation buttons are exercised too.

- `test_dashboard_and_every_incident_render`
- `test_app_injects_no_dynamic_html`
- `test_dashboard_counts_come_from_engine`
- `test_dashboard_falls_back_to_severity_without_engine_classes`
- `test_view_all_opens_security_incidents`
- `test_recent_incident_view_opens_that_incident`
- `test_full_report_dialog_shows_engine_rules`
- `test_search_filters_incident_list`
- `test_unclassified_engine_output_is_never_labelled`
- `test_engine_classification_priority_and_unassigned_severity_render`
- `test_timeline_is_chronological_and_rules_match_engine`
- `test_data_text_is_shown_literally`
- `test_load_error_shows_no_counts`
- `test_validated_report_allows_exactly_one_decision`
- `test_audit_history_shows_decision_and_links_back`
- `test_changing_incident_invalidates_report`
- `test_approve_outcome_describes_the_engine_action`
- `test_recorded_decision_is_shown_after_switching_incidents`
- `test_ai_report_links_and_images_are_not_rendered`
- `test_policy_tab_shows_investigation_guidance`
- `test_filter_options_show_match_counts`
- `test_requesting_a_report_opens_the_ai_analysis_tab`
- `test_invalid_citations_keep_decision_locked`
- `test_provider_failure_offers_retry_without_fabricating`

Manual visual check (headless Microsoft Edge screenshots, 1440px and 1280px wide, sidebar expanded and collapsed): all three pages, every investigation tab, and the generated-report and recorded-decision states (using a canned report, no provider call). The dashboard fits a 1440×900 viewport without scrolling; at 1280px its KPI cards stay one height and every Recent Incidents column is visible. Responsive check at 1100px, 820px (tablet), and 390px (phone): no horizontal page scroll; KPI cards wrap, the dashboard and incident layouts stack, the sidebar starts collapsed on a phone, and every action (View, Request AI Report, Approve/Reject) stays reachable.

Classification, severity, and priority display is tested against real `engine.py` output (INC-1001 SUSPICIOUS/HIGH 65, INC-1002 INSUFFICIENT_EVIDENCE/LOW, INC-1003 NORMAL/NONE with severity "Not assigned"). The pre-classification fallback ("NOT CLASSIFIED", dashboard by severity) is tested with a patched engine result. Still untestable until the backend provides them: partial validation with rejected-record reporting, and audit history that survives an app restart (SQLite).

### `TestReportValidation` (17)

- `test_accepts_report_with_supplied_event_and_policy_citations`
- `test_accepts_lowercase_form_of_allowed_ids`
- `test_rejects_fabricated_or_stale_event_ids`
- `test_rejects_lowercase_fabricated_ids`
- `test_rejects_ids_glued_to_letter_or_underscore_prefix`
- `test_rejects_ids_written_with_unicode_dashes`
- `test_unicode_dash_form_of_allowed_id_does_not_count_as_citation`
- `test_rejects_ids_with_trailing_underscore_suffix`
- `test_policy_id_cannot_satisfy_event_requirement`
- `test_extract_citation_ids_returns_well_formed_ids_in_order`
- `test_extract_citation_ids_handles_uncited_report`
- `test_rejects_policy_that_was_not_retrieved`
- `test_rejects_missing_policy_or_event_citation`
- `test_rejects_uncited_report`
- `test_missing_key_is_a_safe_error`
- `test_provider_failure_is_a_safe_error`
- `test_empty_or_malformed_provider_response_is_a_safe_error`

### `TestProviderBoundary` (16)

- `test_valid_response_returns_stripped_report`
- `test_request_uses_documented_endpoint_timeout_and_payload`
- `test_model_defaults_to_environment_override`
- `test_timeout_is_a_safe_error`
- `test_connection_failure_is_a_safe_error`
- `test_http_errors_are_safe_and_do_not_leak_key`
- `test_http_errors_name_the_cause`
- `test_endpoint_defaults_to_global_and_can_be_overridden`
- `test_timeout_and_connection_errors_name_the_cause`
- `test_exhausted_token_budget_is_explained`
- `test_unicode_dashes_in_ids_are_normalized_before_validation`
- `test_reasoning_block_is_removed_from_report`
- `test_invalid_json_is_a_safe_error`
- `test_non_json_content_type_is_a_safe_error`
- `test_unexpected_response_structures_are_safe_errors`
- `test_missing_or_blank_content_is_a_safe_error`

### `TestPolicyRetrieval` (14)

- `test_documented_defaults`
- `test_bundled_incidents_retrieve_expected_policy_ids`
- `test_finance_policy_only_reaches_finance_incidents`
- `test_every_bundled_incident_has_policy_context`
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

### `TestDataValidation` (7)

- `test_existing_incident_data_is_valid`
- `test_missing_required_incident_field_is_rejected`
- `test_invalid_event_type_and_empty_policy_data_are_rejected`
- `test_optional_location_fields_must_be_text_when_present`
- `test_malformed_json_is_rejected`
- `test_missing_file_is_rejected`
- `test_policy_requires_text`

### `TestGuardBeeDetectionEngine` (16), `TestDynamicScoring` (12) and `TestGuardBeePolicyRetrieval` (3) — `tests/test_engine.py`

- `test_production_suspicious_incident_has_explainable_evidence`
- `test_normal_known_ip_login_has_no_low_severity`
- `test_unfamiliar_ip_alone_is_insufficient_evidence`
- `test_normal_repeated_known_successes`
- `test_known_ip_failure_then_success_is_suspicious`
- `test_failure_burst_inside_default_window`
- `test_failures_outside_burst_window_are_insufficient_evidence`
- `test_out_of_order_timestamps_use_chronology`
- `test_empty_ip_is_insufficient_evidence_not_unfamiliar`
- `test_overlapping_rules_do_not_double_count_failure_points`
- `test_same_failure_burst_with_multiple_successes_scores_rule_003_once`
- `test_independent_patterns_add_sign_ins_and_ips_without_double_counting`
- `test_finance_and_non_finance_identical_pattern_score_parity`
- `test_risk_score_and_classification_remain_separate`
- `test_score_is_capped_at_100`
- `test_configurable_burst_window_parameter`
- `test_severity_band_edges` (0, 14, 15, 39/40, 64/65, 84/85, 100)
- `test_priority_follows_severity`
- `test_burst_points_grow_per_failure_up_to_30`
- `test_fast_burst_scores_more_than_slow_burst`
- `test_each_extra_sign_in_adds_five_up_to_25`
- `test_new_country_needs_a_known_home_and_a_located_sign_in`
- `test_impossible_travel_within_three_hours`
- `test_off_hours_sign_in_adds_four`
- `test_known_only_sign_ins_lower_the_score_but_stay_suspicious`
- `test_context_signals_never_make_activity_suspicious`
- `test_rule_points_add_up_to_every_bundled_score`
- `test_bundled_scores_spread_across_every_severity`
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
