# API Design

## Implemented provider contract

`ai_client.py` uses the OpenAI Python SDK with the fixed `BASE_URL` value `https://api.tokenfactory.us-central1.nebius.com/v1/`. It initializes `OpenAI(base_url=BASE_URL, api_key=..., timeout=60.0)` and calls chat completions with temperature `0.2` and maximum 750 tokens.

## Configuration

| Input | Current behavior |
| --- | --- |
| `NEBIUS_API_KEY` | Required. Read from Streamlit Secrets first, then environment. |
| `NEBIUS_MODEL` | Optional. Read from Streamlit Secrets or environment; falls back to the code default. |
| `NEBIUS_BASE_URL` | Not currently configurable; the base URL is a source constant. |
| `NEMOTRON_MODEL` | Not currently read; use `NEBIUS_MODEL`. |

Never place real values in documentation, code, test fixtures, or tracked config.

## Prompt and validation

The system prompt requires cautious, evidence-only analysis, separates observed facts from potential impact, asks for concise Markdown sections, requires `EVT-*` and `POL-*` citations, and prohibits claiming an action executed. The user message serializes current incident, deterministic analysis, and retrieved policy data.

The validator rejects empty reports; unknown/stale event IDs; unretrieved policy IDs; and reports without at least one current event ID and one retrieved policy ID. It only proves ID membership, not the semantic correctness of each sentence.

## Error behavior and status

Missing keys, SDK/provider exceptions, and malformed/empty responses produce `AIReportError`. The UI displays an actionable error and keeps approval disabled. No live key, account-specific model call, response latency, or provider benchmark has been verified in this repository.
