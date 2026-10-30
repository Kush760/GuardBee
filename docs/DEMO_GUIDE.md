# Demo Guide (MVP v2.2)

## Startup

```powershell
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt   # if needed
streamlit run app.py
```

Configure `NEBIUS_API_KEY` only if you will show a live AI report.

## UI navigation

Sidebar pages:

1. **Dashboard** — total incidents, classification KPIs, donut chart, recent incidents with View.
2. **Security Incidents** — search, filter, list, investigation workspace.
3. **Audit History** — session decisions, filters, row detail, open incident.

Sidebar also shows demo-only notice, Nebius key status, model name, and session decision count.

## Investigation flow

1. Open **Security Incidents** and select e.g. a high-interest incident from the list.
2. Review header KPIs: risk score, severity, priority (from `engine.py`).
3. **Timeline** — events with evidence highlighting.
4. **Rules & Evidence** — rule hits, observed facts, engine interpretation, unknowns.
5. **Relevant Policies** — TF-IDF matches ≥ `DEFAULT_MIN_SIMILARITY` (0.08).
6. Click **Request AI Report** (disabled when no policy match).

## Policy evidence

Matched passages show id, title, similarity, text, and optional investigation guidance. No match → warning; AI and decisions unavailable.

## AI report workflow

- Spinner while calling Nebius; failures set `report_status` and do not fabricate text.
- Success requires citation validation against current event IDs and matched policy IDs.
- AI Analysis tab shows validated citations and Markdown report.
- Caption clarifies citations ≠ semantic proof.

## Simulated decisions

- Approve / Reject unlock only when `can_record_decision` is true.
- Outcomes are labeled simulation-only; no external systems change.
- One decision per active validated report id; switching incidents clears report state.

## Audit history behavior

- Lists `session_state.audit` newest-first with filters.
- UI warns that storage is session-only (SQLite module not wired).
- Click a row for detail; optional navigation back to the incident.

## Demo limitations

- Synthetic data; not live monitoring.
- Live AI depends on key, quota, model, and network.
- Audit does not survive restart in the current UI.
- Do not claim real containment occurred.
