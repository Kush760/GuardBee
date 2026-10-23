# MVP Workflow

## 1. Security Dashboard

The analyst selects one of the validated synthetic incidents. The dashboard displays incident count, deterministic risk score, severity, and supporting-event count.

## 2. Incident Investigation

GuardBee displays the synthetic account, department, full event timeline, rule hits, and evidence IDs. `engine.py` supplies the deterministic score; no model participates in this step.

## 3. Company Policy Check

The application creates a query from incident title, department, rule flags, and suggested action. `retrieval.py` returns up to three policies meeting the `0.08` cosine-similarity threshold. A no-match state is shown explicitly.

## 4. AI Security Analysis

When there is a policy match and the analyst clicks Analyze, GuardBee sends current synthetic incident facts, deterministic analysis, and retrieved policies to the configured Nebius endpoint. A report must cite current `EVT-*` IDs and retrieved `POL-*` IDs. Missing credentials, provider failures, malformed output, no policy match, or citation failure keep the report invalid and approval disabled.

## 5. Response and Audit

One validated report can receive either Approve simulated response or Reject recommendation. The app records a session-only audit event and disables both controls for that report. A new AI analysis creates a new report ID; selecting a different incident invalidates the active report.

The application performs no real remediation. See [workflow diagram](diagrams/workflow.mmd).
