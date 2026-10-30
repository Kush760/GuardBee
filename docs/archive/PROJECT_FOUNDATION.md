# GuardBee Project Foundation

## Purpose

GuardBee helps a security analyst investigate a synthetic suspicious-login alert. The MVP brings together event evidence, transparent rule-based risk (including `NORMAL` / `SUSPICIOUS` / `INSUFFICIENT_EVIDENCE`), relevant sample policy passages, optional live AI explanation, and a human-controlled simulated outcome in one short workflow.

## Intended user

The intended user is a small-company IT or security analyst who needs a clear starting point for a suspicious-login review. GuardBee is a demonstration tool, not a replacement for an incident-response program or a security operations center.

## User journey

1. Select one synthetic login incident.
2. Inspect its event timeline, classification, risk score, severity (when applicable), rule hits, and event IDs.
3. Review policy passages retrieved from the bundled sample policy library.
4. Request a live Nebius Token Factory/NVIDIA Nemotron explanation when a policy match exists and credentials are configured.
5. Review a report that cites current event and retrieved-policy IDs.
6. Approve or reject one simulated outcome for that report; view the SQLite-backed simulated audit history (mirrored in session state for display).

## Scope boundaries

GuardBee uses only bundled synthetic JSON data. The application does not connect to identity providers, employee accounts, SIEM/SOC tooling, or infrastructure for real containment. Approving an action records a simulation-only audit row in local SQLite (`audit_store.py`); it cannot revoke a session, reset a password, disable an account, or make an external change.

## Safety principles

- Deterministic code, rather than AI, establishes classification, risk score, and severity.
- Policy and event text are treated as evidence, not executable instructions.
- An AI report is never fabricated. Missing credentials, provider failures, empty responses, invalid citations, and missing policy matches keep approval unavailable.
- Citation IDs are checked against the current incident and the policies retrieved for that analysis. This confirms identifier membership only; it does not prove every model statement is semantically supported.
- Simulated audit history persists locally in SQLite across app restart and must still not be presented as production compliance evidence.

## Current delivery state

This repository contains the local application, synthetic inputs, automated tests, and documentation. It does not include a deployment URL, a configured Nebius credential, or a claim of successful live model inference unless separately verified.
