# GuardBee — MVP Scope & Working Guide

**Version:** MVP scope reference v2.2  
**Purpose:** A concise source of truth for the work GuardBee must include in the MVP.  
**Status:** Scope decisions below are agreed in conversation. Final repository reconciliation is pending; code implementation is not confirmed complete or authorized by this document.

## 1. MVP goal and workflow

GuardBee analyzes synthetic login events, identifies potentially suspicious authentication patterns, calculates a contextual risk score, explains findings using relevant local policies, and records simulated analyst decisions in a persistent audit history.

1. Load the static synthetic dataset from `data/incidents.json`.
2. Validate incidents and events. Process valid records and report invalid records separately; do not silently discard invalid data.
3. Classify activity as normal, suspicious, or insufficient evidence.
4. Analyze timestamps, chronological order, failed-attempt sequences and gaps, IP familiarity, login outcomes, evidence quality, and relevant asset context.
5. Apply detection rules and calculate a contextual risk score without repeatedly counting the same evidence.
6. Determine severity and investigation priority separately from the numeric score and activity classification.
7. Retrieve relevant policies from `data/policies.json`.
8. Generate an evidence-grounded explanation using the configured AI provider (Nebius/Nemotron, subject to the existing integration).
9. Validate policy citation IDs and prevent unsupported claims.
10. Show findings and evidence in the existing UI.
11. Allow one simulated Approve or Reject decision per validated AI report and persist it in SQLite.
12. On AI/provider failure, show an error and allow retry; do not fabricate an explanation.

## 2. Activity classification

- **Normal activity:** Genuine, expected logins are not listed as suspicious incidents and must not receive LOW severity.
- **Suspicious activity:** Evidence supports investigation; show the relevant events and explain why the pattern is suspicious.
- **Insufficient evidence / unconfirmed:** Preserve uncertainty when the data does not support a confident normal or suspicious conclusion. Do not claim confirmed compromise.
- A numeric score of zero alone does not prove that an event is genuine.
- Normal events must still be processed and counted correctly.

## 3. Scoring rules and decisions

### Known-IP failures followed by success

Use a contextual score based on timestamps, event sequence, number and spacing of failures, successful outcome, IP familiarity, and other available evidence.

- A known IP is a context signal, not a guarantee of safety.
- Detect failure bursts with a configurable time window.
- Also evaluate longer-term patterns separately.
- Preserve chronological order when evaluating event sequences.
- Closely grouped failures followed by success may be more suspicious than failures spread over a long period.
- Do not automatically label every failure-then-success sequence high risk; evaluate the complete evidence.

### Successful login from an unfamiliar IP with no failures

- Unfamiliar IP alone must not automatically mean malicious activity or confirmed compromise.
- If no other suspicious evidence exists, preserve the case as insufficient evidence / unconfirmed rather than claiming compromise.
- Do not list it as a suspicious incident solely because the IP is unfamiliar.
- Keep insufficient evidence distinct from normal activity when the data cannot establish that the login is genuine.

### Avoid duplicate scoring

Use a hybrid approach:
- Independent suspicious signals can contribute to the score.
- Multiple rules triggered by the same underlying evidence must not repeatedly inflate the score.
- Make rule contributions traceable to events/evidence.
- Cap the overall score at 100.

### Score, severity, and priority

Keep these concepts separate:
- **Risk score:** numeric estimate based on available evidence.
- **Severity:** category derived from the scoring policy.
- **Investigation priority:** urgency of analyst review, considering evidence and relevant asset criticality.
- HIGH risk is not proof of compromise. Distinguish observed facts, inferred risk, and unknowns in explanations.

Initial thresholds to retain and test:
- **HIGH:** score ≥ 70
- **MEDIUM:** score 30–69
- **LOW:** score < 30

These are baseline thresholds. Test representative normal and suspicious cases and calibrate if the evidence supports a change. Normal activity must not receive LOW severity.

## 4. Synthetic data and validation

- Input: static `data/incidents.json`; no upload UI.
- Use synthetic records only, including both genuine/normal and suspicious login events.
- Include enough fields to support analysis: incident ID/title/description, account or asset context, unique event IDs, event types, UTC timestamps, source IPs, known-IP context, failure sequence and gaps, evidence references, and expected scenario/outcome where useful.
- Cover normal activity, false positives, false negatives, known-IP failure-then-success, unfamiliar-IP success without failures, chronology, time windows, overlapping rules, and insufficient evidence.
- Process valid records and report invalid records separately; never silently discard invalid records.
- Keep the fixture schema consistent with the actual data loader and tests.

## 5. Policies and AI explanation

- Policy source: local `data/policies.json`.
- Detection rules identify patterns and score evidence; policies guide interpretation and investigation.
- Policy entries need stable IDs, titles, descriptions, applicable conditions/categories, and investigation guidance.
- Retrieve relevant policies and provide them as context to the configured AI provider.
- Validate policy citation IDs against the available policy set.
- Explanations must be grounded in actual events and retrieved policies; do not invent evidence or certainty.
- On provider failure or unusable output, show an error and offer retry.
- Prevent a stale report from being used for a different incident or changed context.

## 6. Simulated decisions and audit history

- Approve/Reject are simulated analyst actions only.
- Each validated AI report permits exactly one decision: Approve or Reject.
- Persist audit history in SQLite, not only in session state.
- Store incident/report references, decision, timestamp, relevant evidence/policy references, and status.
- Do not store secrets in audit records.
- Audit history must remain available after app restart.

## 7. UI requirements

Improve the existing workflow and pages:
- Dashboard
- Security Incidents
- Audit History

Clearly distinguish normal activity, insufficient evidence, and suspicious findings. Show risk score, severity, investigation priority, supporting events, policy citations, and AI uncertainty. Do not present a risk score as confirmed compromise. Safely render dynamic incident, policy, and AI content.

## 8. Testing requirements

Retain useful existing tests and add coverage for:
- Normal activity is not given LOW severity.
- Suspicious patterns and insufficient evidence.
- Configurable time-window bursts and longer-term patterns.
- Chronological ordering and known-IP failures followed by success.
- Unfamiliar-IP success with no other suspicious evidence.
- Duplicate-evidence handling and score cap.
- Threshold boundaries and calibration using representative scenarios.
- Partial/invalid input handling.
- Policy citation validation.
- AI/provider failure, retry, and stale-report prevention.
- One decision per validated report.
- SQLite persistence across app restart.

Test modules incrementally and run the full end-to-end suite after integration. Verify the actual repository test command and environment path. Unit-test success alone does not prove the integrated demo works; test the UI workflow where feasible.

## 9. Repository verification and implementation sequence

1. Verify current Git branch, HEAD commit, and `git status`.
2. Preserve uncommitted work, including UI/team changes. Do not discard, overwrite, stash, commit, or switch branches without explicit authorization.
3. Reconcile the current repository against this scope; verify actual paths and code rather than assuming module names.
4. Report confirmed gaps, affected components, and proposed changes.
5. Obtain explicit approval before editing code.
6. Implement the approved changes, add/update tests and relevant docs, and run incremental plus end-to-end tests.
7. Report what changed, what passed, and what remains unresolved.

A prior audit was performed on `feature/ui-polish`, not confirmed on `main`; do not assume its findings exactly describe the current branch. Potentially relevant modules mentioned in the earlier audit include `app.py`, `engine.py`, `data_loader.py`, `retrieval.py`, `ai_client.py`, `workflow.py`, JSON data/policies, tests, and docs—but verify which actually exist.

## 10. Current status

**Agreed:** MVP goal and workflow; static synthetic JSON; valid/invalid record handling; normal vs suspicious vs insufficient-evidence classification; contextual scoring; time-window plus longer-term patterns; chronological ordering; unfamiliar-IP handling; hybrid duplicate-evidence control; score/severity/priority separation; baseline thresholds with test-based calibration; policy-grounded AI and citation validation; provider error/retry behavior; SQLite audit persistence; one simulated decision per validated report; existing UI pages; and comprehensive tests.

**Pending:** Final reconciliation against the current repository and branch, verification of actual implementation and test status, and separate explicit approval before repository changes.

**To restore context in a future chat:** Attach this Markdown file and say: “Treat this as the authoritative GuardBee MVP scope. Summarize it, identify unresolved items, and do not modify code until I explicitly approve implementation.”
