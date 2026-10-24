# Demo Guide

## Under-three-minute judge script

### 0:00–0:20 — Problem and boundary

"Suspicious-login alerts require connecting raw event logs, company policy, and a human decision.
GuardBee demonstrates that workflow end-to-end using synthetic data only; it never changes a real account."

Point to the **safety banner** at the top of the page to confirm the synthetic/simulation scope.

### 0:20–0:55 — Sidebar and incident selection

Open the left sidebar. Select **INC-1001 — Suspicious login after repeated failures**.
The sidebar immediately shows the risk score and severity badge for a quick-glance summary.

Switch to the main area and click the **Investigate** tab.

### 0:55–1:25 — Investigation tab

Show the **Incident Context** card: account, department (Finance — labelled "Sensitive"), and incident ID.

Scroll to the **Event Timeline**:
- Unfamiliar IPs are highlighted with a flag icon and shown in amber.
- All Event IDs, timestamps, IP addresses, and countries are displayed exactly as recorded.

Show the **Deterministic Rule Evidence** cards — each fired rule is presented with:
- Its rule ID (e.g. `GB-RULE-001`), flag description, point contribution, and linked `EVT-*` evidence IDs.
- State explicitly: "These facts come from deterministic Python rules, not AI."

The **Suggested Action** card summarises the engine's recommendation.

### 1:25–1:45 — Policy Retrieval tab

Click the **Policy Retrieval** tab. Show the retrieved `POL-*` policy cards with:
- Policy ID badge, title, and TF-IDF similarity bar with score.
- Policy text clearly labelled as reference material, distinct from incident evidence.

Explain that passages below the 0.08 threshold are excluded and that no match blocks AI analysis.

### 1:45–2:15 — AI analysis (within Investigate tab)

Return to the **Investigate** tab and scroll to the AI section below the evidence.

If a verified Nebius configuration is available:
- Click **Analyze with AI →** and point to the spinner message.
- After the report loads, show the citation-validation success message and rendered markdown report.
- Explain the citation gate: "Approve/Reject unlock only if the report cites actual EVT-* and POL-* IDs from this analysis."

Without a configured key:
- Show the safe info message: no key details or raw provider response are displayed.
- Approval remains disabled — demonstrate the locked gate message in the Decision tab.

### 2:15–2:40 — Decision & Audit tab

Click the **Decision & Audit** tab. Show the proposed action and the simulation disclaimer.

After a valid report: click **Approve Simulated Response** or **Reject Recommendation**.
Show the decision result card and the updated audit history table below.
Confirm that the buttons lock immediately and explain: "One decision per AI analysis. A new analysis enables one new decision."

### 2:40–3:00 — Safety close

Summarise:
- Risk score: deterministic rules only, not AI.
- Policy evidence and AI citations: visible and validated.
- Human approval gate: citation-validated before unlock.
- Audit log: session-only, temporary.

Point to the scope boundary: "No real session, account, or password is changed. All IPs and accounts are synthetic."
