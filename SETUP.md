# AI Workflow Auditor — Setup & Usage Guide

## What This Is

A modular Python tool that diagnoses your workflow, identifies inefficiencies, designs an optimised AI-powered system, and calculates your exact ROI. Two interfaces: CLI and Streamlit web UI.

---

## 1. Prerequisites

- Python 3.9 or higher
- A DeepSeek API key — get one free at [platform.deepseek.com](https://platform.deepseek.com/api_keys)

---

## 2. Installation (3 steps)

```bash
# Step 1 — Navigate to the project folder
cd ai_workflow_auditor

# Step 2 — Install dependencies
pip install -r requirements.txt

# Step 3 — Set up your environment
cp .env.example .env
# Then open .env and paste your DeepSeek API key
```

---

## 3. Running the Tool

### Option A — Streamlit Web UI (recommended)
```bash
streamlit run app.py
```
Opens at `http://localhost:8501` — fill in the form and click **Run Audit**.

### Option B — CLI with demo data
```bash
python main.py --demo
```

### Option C — CLI with your own JSON
```bash
python main.py --file sample_input.json
```

### Option D — Interactive CLI prompts
```bash
python main.py
```

### Custom hourly rate (affects ROI calculation)
```bash
python main.py --demo --hourly 100
```

---

## 4. Input Format (JSON)

```json
{
  "role": "Your job title",
  "industry": "Your industry",
  "tasks": [
    {"task": "Descriptive task name", "time_per_week_hours": 5},
    {"task": "Another task",          "time_per_week_hours": 3},
    {"task": "Third task",            "time_per_week_hours": 2}
  ],
  "tools_used": ["Tool1", "Tool2"],
  "pain_points": ["pain point 1", "pain point 2"]
}
```

**Validation rules:**
- Minimum 3 tasks required
- Task names must be ≥5 characters (be descriptive)
- Hours must be numeric, between 0.25 and 80
- `tools_used` and `pain_points` can be empty lists

---

## 5. Output Files

All reports are saved to `reports/` folder:

| File | Description |
|------|-------------|
| `audit_report_TIMESTAMP.md` | Full Markdown report — all 7 sections |
| `audit_report_TIMESTAMP.pdf` | Professionally styled PDF — same content |

---

## 6. Architecture

```
ai_workflow_auditor/
│
├── main.py              ← CLI entry point
├── app.py               ← Streamlit UI
├── input_handler.py     ← Load from file / dict / CLI
├── validator.py         ← Input validation rules
├── processor.py         ← Task classification + inefficiency detection
├── roi_engine.py        ← Deterministic ROI calculation
├── ai_engine.py         ← DeepSeek API integration + fallback
├── report_generator.py  ← Markdown + PDF report generation
├── utils.py             ← Shared utilities
│
├── requirements.txt
├── .env.example         ← Copy to .env and add your key
├── sample_input.json    ← LinkedIn Creator demo data
└── reports/             ← Generated reports (auto-created)
```

---

## 7. DeepSeek API Integration

The tool uses DeepSeek's OpenAI-compatible API via the `openai` Python SDK.

**Endpoint:** `https://api.deepseek.com`  
**Model:** `deepseek-chat`  
**Used for:** Sections 3, 4, 5, and 7 of the report only.

Sections 1, 2, and 6 are always deterministic — they work with or without the API key.

**If the API is unavailable:** The tool automatically falls back to a deterministic version of all sections. You still get a complete, usable report.

---

## 8. Customisation

### Change default hourly rate
Edit `roi_engine.py`, line:
```python
DEFAULT_HOURLY_VALUE = 50.0  # Change to your rate
```

### Add new task categories
Edit `processor.py` — add keywords to the relevant list:
```python
REPETITIVE_KEYWORDS = [..., "your keyword"]
```

### Adjust reduction factors
Edit `processor.py`:
```python
REDUCTION_FACTORS = {
    "repetitive":    0.65,  # 50-80% range, adjust as needed
    ...
}
```

---

## 9. Example Run Output

```
  [1/4] Processing workflow — classifying tasks & detecting inefficiencies...
  [2/4] ROI engine — calculating time savings and automation score...
  [3/4] AI analysis — calling DeepSeek...
         ✅ AI analysis complete
  [4/4] Generating reports — Markdown + PDF...

  ══════════════════════════════════════════════════════════════
    AUDIT COMPLETE — RESULTS SNAPSHOT
  ══════════════════════════════════════════════════════════════

    Role     : LinkedIn Creator
    Industry : Personal Branding

    📋 Tasks analysed    : 4
    ⏱  Total weekly time : 22.0h
    ⚠  Inefficiencies    : 3

    ── ROI SNAPSHOT ───────────────────────────────────
    Time saved / week   : 9.2h
    Efficiency gain     : 41.8%
    Automation score    : 74 / 100
    Annual hours saved  : 478h
    Annual value        : $23,920

  📄 REPORTS SAVED:
     Markdown : reports/audit_report_2026-04-27_10-30-00.md
     PDF      : reports/audit_report_2026-04-27_10-30-00.pdf
```
