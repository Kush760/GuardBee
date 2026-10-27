# Demo Guide

## Under-three-minute judge script

### 0:00-0:20 - Problem and boundary

“Suspicious-login alerts often require connecting logs, policy, and a human decision. GuardBee demonstrates that workflow using synthetic data only; it never changes a real account.”

### 0:20-0:50 - Dashboard and investigation

Use the classification filter (`SUSPICIOUS` / `NORMAL` / `INSUFFICIENT_EVIDENCE`). Select `INC-1001` under Suspicious. Show classification, investigation priority, score 70/100, severity HIGH (not `None`), rule hits, and `EVT-*` IDs. Switch to Normal (`INC-1003`) and Insufficient (`INC-1002`) to show that normals are not presented as suspicious and insufficient is not confirmed compromise. Facts come from Python rules, not AI.

### 0:50-1:15 - Policy retrieval

Open Company Policy Check. Show the matching `POL-*` passages and their TF-IDF scores. Explain that below-threshold passages are not labelled relevant.

### 1:15-1:55 - AI analysis

If a verified authorized Nebius configuration is available, request the live analysis and show current event/policy citations. Do not claim live inference if it has not been tested. Without it, show the missing-key/failure behavior and explain that approval remains locked.

### 1:55-2:30 - Human decision and audit

After a valid report, choose one simulation-only outcome. Show the audit row and locked controls. State that another decision requires a new AI analysis, no real session is revoked, and audit rows persist in local SQLite across restart.

### 2:30-2:50 - Safety and close

Summarize: deterministic risk, visible policy evidence, citation-gated AI, human approval, and SQLite-backed simulated audit. Point out the scope boundaries and current external verification status honestly.
