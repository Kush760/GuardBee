# GuardBee Project Foundation

## Purpose

GuardBee helps a security analyst investigate a synthetic suspicious-login alert. The MVP brings together event evidence, transparent rule-based risk, relevant sample policy passages, optional live AI explanation, and a human-controlled simulated outcome in one short workflow.

## Intended user

The intended user is a small-company IT or security analyst who needs a clear starting point for a suspicious-login review. GuardBee is a demonstration tool, not a replacement for an incident-response program or a security operations center.

## User journey

1. Select one synthetic login incident.
2. Inspect its event timeline, risk score, severity, rule hits, and event IDs.
3. Review policy passages retrieved from the bundled sample policy library.
4. Request a live Nebius Token Factory/NVIDIA Nemotron explanation when a policy match exists and credentials are configured.
5. Review a report that cites current event and retrieved-policy IDs.
6. Approve or reject one simulated outcome for that report; view the temporary session audit record.

## Scope boundaries

GuardBee uses only bundled synthetic JSON data. The application does not connect to identity providers, employee accounts, security tooling, databases, or infrastructure. Approving an action records only an in-memory demo audit event; it cannot revoke a session, reset a password, disable an account, or make an external change.

## Safety principles

- Deterministic code, rather than AI, establishes risk score and severity.
- Policy and event text are treated as evidence, not executable instructions.
- An AI report is never fabricated. Missing credentials, provider failures, empty responses, invalid citations, and missing policy matches keep approval unavailable.
- Citation IDs are checked against the current incident and the policies retrieved for that analysis. This confirms identifier membership only; it does not prove every model statement is semantically supported.
- Audit history is temporary Streamlit session state and must not be presented as durable compliance evidence.

## Current delivery state

This repository contains the local application, synthetic inputs, automated tests, and documentation. It does not include a deployment URL, a configured Nebius credential, or a claim of successful live model inference.
