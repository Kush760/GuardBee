# Quick Start & Usage Guide

A simple, step-by-step guide to run and use **GuardBee**.

---

## 1. Where Is the Frontend?

GuardBee uses **Streamlit**. The frontend UI is served locally and accessed directly via your web browser:

- **Local UI URL:** [http://localhost:8501](http://localhost:8501)
- **Main App File:** `app.py` (handles the dashboard, components, and session state)

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

1. **Select an Incident:**
   - Use the dropdown in the sidebar to choose a synthetic incident (e.g., `INC-2024-001`).
   - The dashboard populates the incident summary and timestamped login events timeline.

2. **Inspect Risk & Evidence:**
   - View the deterministic risk score (0–100), severity tier, and rule breakdown with supporting `EVT-*` evidence IDs.

3. **Review Retrieved Policies:**
   - Inspect visible company security policies (`POL-*`) matched via TF-IDF similarity.

4. **Generate AI Analysis:**
   - Click the button to trigger NVIDIA Nemotron analysis through Nebius Token Factory.
   - The response grounds its recommendation using visible `EVT-*` and `POL-*` IDs.

5. **Submit Analyst Decision:**
   - Once a grounded report is generated, the **Approve** and **Reject** containment actions become unlocked.
   - Recording an action updates the in-memory session audit trail.

---

## 5. Running Automated Tests

To run the full test suite and verify system health:

```powershell
python -m unittest discover -s tests -v
```
