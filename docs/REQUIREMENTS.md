# Requirements

## Functional requirements

| ID | Requirement | Implemented evidence |
| --- | --- | --- |
| FR-01 | Load non-empty synthetic incident and policy JSON safely. | `data_loader.py` validates files and `app.py` stops on failure. |
| FR-02 | Show incident timeline, account, department, rule evidence, score, and severity. | `app.py` plus `engine.analyze_incident`. |
| FR-03 | Derive risk deterministically from login events. | `engine.py`; no AI determines risk. |
| FR-04 | Retrieve sample policies using local TF-IDF similarity. | `retrieval.retrieve_policies`. |
| FR-05 | Exclude below-threshold policy matches. | `DEFAULT_MIN_SIMILARITY = 0.08`. |
| FR-06 | Request optional Nemotron explanation through Nebius Token Factory. | `ai_client.generate_report`; external access unverified. |
| FR-07 | Reject missing, unknown, stale, or unretrieved citation IDs. | `validate_report_citations`. |
| FR-08 | Permit one Approve or Reject action for a current validated report. | `workflow.build_decision_record`. |
| FR-09 | Record a session-only simulated audit result. | Streamlit `session_state.audit`. |

## Non-functional requirements

| ID | Requirement |
| --- | --- |
| NFR-01 | Use synthetic data only and make no real account or system change. |
| NFR-02 | Keep secrets outside source control via Streamlit Secrets or environment variables. |
| NFR-03 | Preserve deterministic investigation behavior if AI is unavailable. |
| NFR-04 | Fail safely on invalid data, missing keys, provider errors, malformed reports, or invalid citations. |
| NFR-05 | Keep tests offline through mocked provider behavior and synthetic data. |
| NFR-06 | Keep audit data explicitly temporary and session scoped. |
