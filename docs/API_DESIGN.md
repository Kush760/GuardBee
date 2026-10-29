# API Design

## Implemented provider contract

`ai_client.py` uses the OpenAI Python SDK with `BASE_URL` `https://api.tokenfactory.nebius.com/v1/` (the global endpoint from the Nebius quickstart), overridable with `NEBIUS_BASE_URL` in Streamlit secrets or the environment. It initializes `OpenAI(base_url=..., api_key=..., timeout=60.0, max_retries=1)` and calls chat completions with temperature `0.2` and maximum 2000 tokens (the reasoning model needs room before it writes). Failures raise `AIReportError` with a cause-specific message (401, 403, 404, 429, timeout, network, exhausted token budget) that never includes provider response text.

## Configuration

| Input | Current behavior |
| --- | --- |
| `NEBIUS_API_KEY` | Required. Read from Streamlit Secrets first, then environment. |
| `NEBIUS_MODEL` | Optional. Read from Streamlit Secrets or environment; falls back to the code default. |
| `NEBIUS_BASE_URL` | Not currently configurable; the base URL is a source constant. |
| `NEMOTRON_MODEL` | Not currently read; use `NEBIUS_MODEL`. |

Never place real values in documentation, code, test fixtures, or tracked config.

## Prompt and validation

The system prompt requires cautious, evidence-only analysis and asks for concise Markdown sections: *Observed facts*, *Inferred risk*, *Unknowns and limitations*, *Policy guidance*, and *Recommended action*. It states that the deterministic risk score is an estimate, not proof of compromise, forbids claiming a confirmed compromise or an executed action, and requires `EVT-*` and `POL-*` citations. Whether a live model follows these sections has not been verified. The user message serializes current incident, deterministic analysis, and retrieved policy data.

The validator rejects empty reports; unknown/stale event IDs; unretrieved policy IDs; and reports without at least one current event ID and one retrieved policy ID. ID comparison is case-insensitive, so `pol-001` counts as a citation of a retrieved `POL-001`, while `evt-999` is rejected as unknown. Disguised IDs are rejected as malformed even when the rest matches an allowed ID: IDs written with a Unicode dash (for example `EVT‑006`), IDs glued to a preceding letter, digit, or underscore (`xPOL-009`, `_EVT-006`, which includes Markdown `_italic_` IDs), and IDs containing underscores (`EVT-999_x`). It only proves ID membership, not the semantic correctness of each sentence. IDs written with spaces (`EVT 999`) are not recognized as citations. Before validation, `generate_report` rewrites look-alike dashes inside EVT/POL IDs (for example the non-breaking hyphen U+2011 that reasoning models emit) as ASCII hyphens, so the displayed and validated text are identical; a normalized ID must still be a current ID, and the validator itself still rejects any un-normalized Unicode-dash ID.

`extract_citation_ids(report)` returns the well-formed `EVT-*` and `POL-*` IDs a report cites (uppercased, first-cited order). It shares its ID scanning with the validator. The UI uses it to show which evidence and policies a validated report cited.

## Error behavior and status

Missing keys, SDK/provider exceptions, and malformed/empty responses produce `AIReportError`. Offline tests drive the real OpenAI SDK through an in-process `httpx.MockTransport` and cover timeouts, connection failures, HTTP 401/403/404/429/500/503, invalid JSON, non-JSON bodies, missing or empty choices, missing or blank content, and a successful response. They also check that the error message never contains the API key, even when the provider echoes it. `AIReportError` messages are fixed strings; the provider exception is chained as `__cause__` and is not shown by the UI. The SDK's default retry behavior (`max_retries=2`) is unchanged and not configured by GuardBee. The UI displays an actionable error and keeps approval disabled. No live key, account-specific model call, response latency, or provider benchmark has been verified in this repository.
