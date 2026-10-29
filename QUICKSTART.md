# Quick Start & Usage Guide

A simple, step-by-step guide to run and use **GuardBee**.

---

## 1. Where Is the Frontend?

GuardBee uses **Streamlit**. The frontend UI is served locally and accessed directly via your web browser:

- **Local UI URL:** [http://localhost:8501](http://localhost:8501)
- **Main App File:** `app.py` (Dashboard, Security Incidents, and Audit History via Streamlit navigation)

When you run the app, Streamlit starts the local server and automatically launches this URL in your default browser.

---

## 2. Installation & Setup

Open PowerShell or your command terminal in the project root directory:

### Step 1: Create and activate virtual environment

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

*(On macOS/Linux, run: `source .venv/bin/activate`)*

### Step 2: Install dependencies

```powershell
pip install -r requirements.txt
```

> **Note:** If you are running in your base Python environment and already have `streamlit`, `scikit-learn`, and `openai` installed, you can skip this step or run `python -m streamlit run app.py` directly.

### Step 3: Set up secrets (Optional for AI analysis)

If you wish to test live AI reports via Nebius Token Factory:

```powershell
Copy-Item .streamlit\secrets.toml.example .streamlit\secrets.toml
```

Edit `.streamlit/secrets.toml`:

```toml
NEBIUS_API_KEY = "your-nebius-api-key"
NEBIUS_MODEL = "nvidia/nemotron-3-super-120b-a12b"
```

> **Note:** The core incident explorer, deterministic risk scoring, and policy retrieval work without an API key. Live AI reports require a valid key. Never commit `.streamlit/secrets.toml`.

---

## 3. Starting the Project

Run the following command:

```powershell
streamlit run app.py
```

Streamlit will print the local URL and automatically open GuardBee in your browser:
```text
Local URL: http://localhost:8501
```

---

## 4. How to Use GuardBee

Once loaded at `http://localhost:8501`:

1. **Dashboard:** Review KPI counts (including rejected records from partitioned loading) and open a recent incident, or use **Security Incidents** in the sidebar.

2. **Select an Incident:**
   - Use the searchable incident picker (for example `INC-1001`).
   - Inspect the chronological timeline, rules/evidence, and retrieved policies.

3. **Generate AI Analysis:**
   - Click **Request AI Report** to call NVIDIA Nemotron via Nebius Token Factory when a key is configured.
   - Success or failure feedback appears in the investigation view; Approve/Reject stay locked until citations validate.

4. **Submit Analyst Decision:**
   - After a citation-validated report, **Approve** or **Reject** records a simulated decision only.

5. **Audit History:**
   - Open **Audit History** to review persisted SQLite rows (`data/audit.db`), including evidence IDs, policy IDs, and report context. Rows survive app restarts.

---

## 5. Running Automated Tests

To run the full test suite and verify system health:

```powershell
python -m unittest discover -s tests -v
```
