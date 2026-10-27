# Test Plan

## Strategy

GuardBee uses offline unit tests for pure logic and mocks for provider failures. Tests must never require a real key, network access, or model endpoint.

| Area | Automated coverage | Manual verification |
| --- | --- | --- |
| Data contract | Valid source data, missing fields/files, malformed JSON, invalid types, empty policies | Edit a copy of sample data and verify actionable Streamlit stop state. |
| Risk engine | High, medium, low, and 30-point severity boundary | Inspect rule rows and event IDs for all incidents. |
| Retrieval | Ranked result, zero match, empty query/data, high threshold exclusion | Confirm visible matches correspond to selected synthetic incident. |
| AI boundary | Missing key, mocked exception, empty/malformed response, citation acceptance/rejection | With authorization, request one live report and inspect allowed IDs. |
| Decision workflow | Duplicate/conflict rejection, new analysis, stale context, changed policy context | Confirm buttons unlock only for current valid report and relock after decision. |

## Entry and exit criteria

Before merge, all unit tests pass and no source/data/secrets boundary is violated. Before submission, the manual browser and authorized live-provider checks in `TESTING.md` must have observed evidence. No test pass substitutes for an untested provider or deployment.
