# GuardBee — User Guide

**Version:** MVP v2.2

## 1. Overview

GuardBee is a demo console for investigating **synthetic** suspicious-login incidents. You review deterministic risk and evidence, related sample policies, an optional AI report, and record a **simulated** Approve or Reject decision.

## 2. Getting started

See [QUICKSTART.md](../QUICKSTART.md) for install and secrets. Launch with `streamlit run app.py`.

## 3. Dashboard

Shows total loaded incidents, classification counts, a classification chart, and recent incidents. Use **View** to jump into Security Incidents for one case.

Data is static JSON, not live monitoring.

## 4. Security Incidents

- Search by id, title, account, or department.
- Filter by classification or severity labels offered in the UI.
- Select an incident from the list.

### Investigation areas

| Area | What you see |
|---|---|
| Header KPIs | Risk score, severity, priority from the engine |
| Basic information | Account, department, known IPs/home, latest event |
| Timeline | Chronological events and evidence markers |
| Rules & Evidence | Rule hits, facts, interpretation, limitations |
| Relevant Policies | TF-IDF matches with similarity scores |
| AI Analysis | Validated report or error/retry |
| Take Action | Simulated Approve / Reject when unlocked |

## 5. AI reports

Request only when policies matched and a Nebius key is configured. Reports must cite current event and policy IDs. Treat inferred risk language as unconfirmed.

## 6. Decisions and audit

Approve/Reject record a simulation-only outcome for the current validated report. Open **Audit History** to filter and inspect decisions from **this session**. They are not written through the SQLite module by the current UI.

## 7. What GuardBee will not do

- Block or unlock real accounts
- Revoke real sessions
- Guarantee that AI text is factually complete
- Persist audit rows across restart in the current UI
