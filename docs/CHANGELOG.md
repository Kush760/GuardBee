# Changelog

## Current MVP

- Built GuardBee as a Streamlit synthetic suspicious-login investigation demo.
- Added deterministic risk scoring, local TF-IDF policy retrieval, optional Nebius/Nemotron client boundary, human simulation, and session audit.

## Reliability and safety updates

- Added single-decision report lock to prevent duplicate/conflicting simulation outcomes.
- Added `0.08` minimum TF-IDF similarity and explicit no-match behavior.
- Added JSON schema validation and safe UI stop path.
- Strengthened current-context event/policy citation checks.
- Expanded the unit suite from 6 to 25 tests.

## Workstream D - policy retrieval and AI boundary hardening

- Citation validation now compares IDs case-insensitively and rejects fabricated IDs hidden by lowercase, Unicode dashes, glued letter/digit/underscore prefixes, or underscore suffixes.
- Added `DEFAULT_TOP_K = 3` to `retrieval.py` (no ranking change). Added argument and policy-entry validation, and empty-vocabulary corpora now return no matches instead of raising.
- Added `tests/test_retrieval.py` and offline provider-boundary tests that drive the OpenAI SDK through a mock HTTP transport. The unit suite grew from 25 to 54 tests.
- Unchanged: TF-IDF retrieval, the `0.08` threshold, bundled-incident policy matches, provider endpoint, model, timeout, retries, and the request payload.

## MVP scope Phase A - UI alignment (`dev`)

- Merged the Workstream B four-view UI (`feature/ui-polish`) into `dev`.
- Fixed a navigation bug where "Open"/"Investigate" bounced back to the previous view, making the incident detail, AI analysis, and decision controls unreachable.
- HTML-escaped all incident, event, policy, AI-status, and audit values rendered as raw HTML.
- Removed the UI rule "Normal = severity LOW"; activity classification and investigation priority are shown only when `engine.py` provides them. Severity counts replace the Suspicious/Normal counts.
- Added a "not proof of compromise" note, the evidence and policies cited by a validated AI report, and an explicit Retry after AI failure.
- The AI prompt now requests Observed facts / Inferred risk / Unknowns and limitations sections. Added `extract_citation_ids()`.
- Added headless Streamlit UI tests (`tests/test_app_ui.py`). The suite grew from 54 to 64 tests.

## Native Streamlit UI (`dev`)

- Replaced the custom-HTML dark UI with native Streamlit components and a light honey theme, following the UI Member Frontend Specification: three sidebar pages (Dashboard, Security Incidents, Audit History), no `unsafe_allow_html`, and no external font download.
- Dashboard: valid-incident count, classification counts (shown as "—" until the engine provides classes), severity counts including "Not assigned", fail-closed validation note, overview table, and an "Open in Security Incidents" action.
- Security Incidents: filterable list, incident picker, classification with the specification's required wording, separate score / severity / investigation-priority metrics, a five-step progress bar, chronological timeline, triggered rules with points, observed facts / interpretation / unknowns, policy expanders, a labelled AI-generated section with cited IDs and Retry, and simulated decisions that show the saved time and the reason controls are locked.
- Audit History: newest-first table with an explicit session-only warning until SQLite persistence exists.
- UI tests rewritten for the new pages (12 tests). The suite grew from 64 to 68 tests.

## Security Analytics Console UI (`dev`)

- Restyled the UI as a premium SOC console: navy fixed-width sidebar with a shield logo and highlighted active page (`st.navigation`), light blue-white content area, white cards, indigo accent, and red / green / amber status colours. Styling is centralised in `.streamlit/config.toml` and one static stylesheet; Streamlit's deploy toolbar is hidden.
- Dashboard: five summary cards, a classification/severity overview, a recent-incidents table, and "Open investigation" that switches page and keeps the selection.
- Security Incidents: search and filter list with a selected-incident summary, header card, four indicator cards, the progress steps, tabs (Timeline, Rules & Evidence, Relevant Policies, AI Analysis), evidence references per rule, a "SIMULATED ACTION — NO REAL ACCOUNT ACTION" decision panel, and a link to Audit History.
- Audit History: decision and incident filters, newest-first table, record detail, and a link back to the incident.
- Identifiers render as literal inline code so e-mail addresses are never turned into links; removed the deprecated `use_container_width` argument.
- UI tests rewritten for page navigation (14 tests). The suite grew from 68 to 70 tests.
- Gradient styling: navy-to-indigo sidebar, indigo/violet active page, sidebar demo card and primary buttons, and green/red gradient Approve/Reject once enabled. Summary and indicator cards are tinted by status (blue, rose, green, amber, violet); on the investigation page the tint follows the engine's actual classification and severity. Tints need keyed containers (newer Streamlit); older versions in the allowed range show plain white cards.
- Compact dashboard layout: one-line page subtitle and demo banner, equal-height KPI cards with short captions, a severity-distribution card beside a "Risk score by incident" bar chart (Altair, which ships with Streamlit; fixed 0–100 axis, hover tooltips), and a full-width recent-incidents table with the incident picker and "Investigate →" in its header row. The dashboard fits a 1440×900 screen without scrolling.
- Severity colour coding on the dashboard: HIGH red, MEDIUM amber, LOW blue, Not assigned grey (green stays reserved for the NORMAL classification). Applied to the severity bars, the risk-score chart bars (each labelled with score and severity in text), and the Severity column of the recent-incidents table.
- Dashboard rebuilt to the GuardBee mockup: title with "AI-Powered Security Analysis for Safer Access" and a red Demo Only card; five KPI cards with round status icons (Total valid incidents, Suspicious, Normal, Insufficient evidence with percentages once the engine classifies, and Rejected records = 0 from the fail-closed loader); an Incident Overview donut with total and legend; a Recent Incidents list with classification, score, severity and priority badges, a View button per row and View All; and a Data Source strip. The donut shows classification counts when engine.py provides them and severity counts until then. Not copied from the mockup: the signed-in user avatar (GuardBee has no users or login) and the sample numbers (24 incidents, P1–P3), which the bundled data and engine do not produce. UI tests: 15 (suite 71).
- Official GuardBee logo (bee shield, "GuardBee — Security Analytics Console"): full logo in the dashboard header in place of the text title, the shield with a light wordmark as the sidebar logo, and the shield as the browser-tab icon. Transparent PNGs were cut from the supplied artwork.
- Collapsed sidebar: the top bar shows the bee-shield icon (the white wordmark was invisible on the light bar), gets a light surface, and pushes content below it; the fixed 248px sidebar width now applies only while expanded, so collapsing no longer leaves a blank strip.
- Security Incidents rebuilt to the GuardBee mockup: header with search and filter; an "Incidents (N)" list of selectable cards (status shield, ID, title, classification · score · severity · latest event); an incident header card with the classification badge, the specification wording, a one-line progress trail (Detect → Decision) and "Request AI Report"; Risk score / Severity / Priority cards; a Basic Information grid (account, department, known IPs, latest event, timestamp, source IP and location — no device field, which the data does not contain); tabs with a visual Timeline (red failed / green successful logins, evidence tags, full event table in an expander) beside an Engine Analysis card, Rules & Evidence, Relevant Policies, and AI Analysis; and a bottom row with Relevant Policies and "Take Action (Simulated)" Approve / Reject. Keys and gates are unchanged.
- Interactive Security Incidents view: compact Risk score / Severity / Priority cards (details in tooltips), tinted icon chips on incident cards and the header, a connected vertical timeline with row hover, hover lift on cards and buttons, light "Request AI Report" button, Approve / Reject shown in faded green / red while locked, and "View Full Report" opening a dialog with the engine's rule-by-rule breakdown (no AI content). UI tests: 16 (suite 72).
- Sidebar: navigation stays at the top while the Demo only and AI provider cards are pinned to the bottom (no divider gap), the AI provider details sit in their own card with a status dot, a small footer was added, and the sidebar scrollbar is slim and translucent.
- Dashboard header logo is now an SVG with real text for "GuardBee" and "Security Analytics Console" (the JPEG-derived PNG made the small subtitle blurry); only the bee shield remains a bitmap.
- Removed the red Demo Only card from the dashboard header; the sidebar's Demo only card, visible on every page, keeps the disclaimer.
- Removed the dashboard header (logo and tagline); the dashboard now opens on the KPI cards and the sidebar carries the GuardBee logo. The unused header logo asset was deleted.
- Made the UI responsive. Rows react to the width of the content area (sidebar excluded) through CSS container queries: KPI cards wrap to three, then two per row; the dashboard's overview and recent-incidents cards stack; the incident list stacks above the investigation as a swipeable row of cards; timeline, findings, and policy/decision columns stack on narrow screens. On narrow screens Recent Incidents keeps ID, score, severity, and View (classification and priority remain on the incident page). The sidebar starts collapsed on phones (`initial_sidebar_state="auto"`).
- Adopted the v2.2 data and engine merged in PR #2 (`GuardBee_MVP_v2.2_recovered/`): `engine.py`, `data/incidents.json` (13 incidents, up from 3), and `data/policies.json` (4 policies with categories, conditions, and investigation guidance) now come from v2.2, and `tests/test_engine.py` is the v2.2 engine suite. The UI now shows engine-provided classification and priority; scores change (for example INC-1001 is 70, not 95). INC-1009 matches no policy, so its AI report stays unavailable. Per `RECOVERY_NOTES.md`, titles, accounts, and timestamps for INC-1004 to INC-1013 were reconstructed. The v2.2 `audit_store.py` (SQLite), `data_loader.py` partial validation, and `ui_presentation.py` were not adopted. The suite is now 86 tests.
- Made the "View Full Report" dialog smaller: medium width (750px instead of large) with compact report text. Only the report body scrolls (max 440px, less on short screens); the title, incident summary, and risk note stay fixed. Its scrollbar is hidden; the body still scrolls by wheel, touch, and keyboard.
- QA pass fixes: (1) Approve now records the engine's own suggested action as the outcome; it previously said "session-revocation" for every incident, including NORMAL and INSUFFICIENT_EVIDENCE ones. (2) The decision panel shows the last recorded decision for an incident after you switch away and back, with a link to Audit History. (3) AI report text no longer renders as live Markdown links or images: links and images are reduced to their text, and URLs and email addresses are shown as literal code. (4) Incident filter options show how many incidents each one matches (for example "Low severity (0)"). The suite is now 90 tests.
- AI report failures now name their cause (rejected key, model not available, quota, timeout, network, or an exhausted token budget) without echoing provider text. The client retries once instead of twice, the reply budget rose from 750 to 2000 tokens for the reasoning model, and any `<think>` block is stripped from the report. The suite is now 94 tests.
- The AI report outcome (ready, or the failure reason) now appears in the incident header beside "Request AI Report", not only inside the AI Analysis tab.
- The Nebius endpoint now defaults to the global `https://api.tokenfactory.nebius.com/v1/` from the Nebius quickstart instead of the hard-coded us-central1 regional endpoint, and `NEBIUS_BASE_URL` selects a regional one. A key used on the wrong endpoint returned HTTP 401; the 401 message now names the endpoint. The suite is now 95 tests.
- Spacing fixes: page width cap raised from 1360px to 1640px so wide screens have no large empty gutters; side-by-side cards (Incident Overview and Recent Incidents, Relevant Policies and Take Action) share one height; incident-list captions line up with titles and the list fills its card; Recent Incidents text lines up with the View buttons and "View All" is right-aligned; Basic Information wraps evenly (three fields per line, two on narrow screens).
- The dashboard opens with a "Welcome to GuardBee" heading (subtitle "Security Analytics Console"), matching the title style of the other pages.
- Incident Overview donut is centred in its card and larger (232px instead of 164px across) with a thicker ring, rounded slice ends, small gaps between slices, and a bigger total; the legend is now a centred row of stat blocks below the chart.

## Documentation and delivery assets

- Added structured project, technical, team, quality, diagram, CI, and shareable-handoff documentation.
