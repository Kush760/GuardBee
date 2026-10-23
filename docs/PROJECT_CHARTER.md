# Project Charter

## Vision

GuardBee demonstrates an evidence-first security decision workflow for a synthetic suspicious-login alert. The product connects deterministic evidence, sample policy guidance, optional AI explanation, and an explicitly human-approved simulated response.

## Hackathon objective

The project targets the Nebius Global AI Hackathon delivery window ending October 30. The intended submission demonstrates NVIDIA Nemotron access through Nebius Token Factory when account access is available, while retaining a safe deterministic fallback when it is not.

## Users

Primary users are SOC analysts and small security/IT teams reviewing suspicious-login alerts. The MVP is a demo aid; it is not a production SIEM, SOAR tool, or account-control system.

## In scope

- Synthetic login incidents and sample policies stored as JSON.
- Deterministic risk score, severity, flags, and evidence IDs.
- Local TF-IDF policy retrieval with a minimum score threshold.
- Optional live Nemotron explanation through Nebius Token Factory.
- Current-context ID citation gate, single human decision, and temporary audit history.

## Out of scope

- Real accounts, logs, security integrations, automatic account changes, or durable audit storage.
- Enterprise identity, RBAC, SIEM ingestion, vector databases, custom training, and multi-user workflows.

## Success criteria

A reviewer can inspect a synthetic incident, understand the deterministic rationale, see a valid policy match, safely handle unavailable AI, and record one simulation-only human decision. Live Nebius inference and public deployment remain external verification items until actually tested.
