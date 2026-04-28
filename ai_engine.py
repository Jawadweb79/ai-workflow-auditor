"""
ai_engine.py — DeepSeek API integration for AI Workflow Auditor.

DeepSeek exposes an OpenAI-compatible REST API, so we use the openai SDK.
This module is responsible for ONLY the sections that benefit from language
model reasoning: automation deep-dive, optimised workflow design,
implementation plan, and executive summary.

All deterministic data (classification, ROI, inefficiencies) is computed
in processor.py and roi_engine.py — this module enriches, not replaces.

Graceful fallback: if the API is unavailable or the key is missing,
_generate_fallback_content() returns a fully usable deterministic output.
"""

import os
from typing import Dict, Optional

try:
    from openai import OpenAI
    _OPENAI_AVAILABLE = True
except ImportError:
    _OPENAI_AVAILABLE = False

# ── Configuration ──────────────────────────────────────────────────────────────
DEEPSEEK_BASE_URL = "https://api.deepseek.com"
DEEPSEEK_MODEL    = "deepseek-chat"
MAX_TOKENS        = 2000
TEMPERATURE       = 0.3   # Low for structured, consistent output


# ── Client factory ─────────────────────────────────────────────────────────────

def _get_client() -> "OpenAI":
    """
    Initialise the OpenAI-compatible DeepSeek client.
    Reads DEEPSEEK_API_KEY from environment.
    Raises EnvironmentError if the key is absent.
    """
    if not _OPENAI_AVAILABLE:
        raise EnvironmentError(
            "openai package not installed. Run: pip install openai"
        )
    api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        raise EnvironmentError(
            "DEEPSEEK_API_KEY not found in environment. "
            "Add it to your .env file: DEEPSEEK_API_KEY=sk-..."
        )
    return OpenAI(api_key=api_key, base_url=DEEPSEEK_BASE_URL)


# ── Prompt builder ─────────────────────────────────────────────────────────────

def build_analysis_prompt(analysis: Dict, roi: Dict) -> str:
    """
    Build a structured, role-specific prompt for DeepSeek.
    Embeds all deterministic context so the LLM enriches rather than guesses.
    """
    workflow = analysis["input"]

    tasks_block = "\n".join(
        f"  {i+1}. {ct['task']}  |  {ct['hours']}h/week  |  [{ct['category']}]"
        for i, ct in enumerate(analysis["classified_tasks"])
    )

    ineff_block = "\n".join(
        f"  [{item['severity']}] {item['task']}: {item['reason']}"
        for item in analysis["inefficiencies"]
    ) or "  None flagged by rule engine."

    opps_block = "\n".join(
        f"  - {opp['task']} → {opp['automation_suggestion']}  (Priority: {opp['priority']})"
        for opp in analysis["automation_opportunities"]
    )

    prompt = f"""You are a senior AI workflow consultant specialising in {workflow['industry']}.
Your client is a {workflow['role']} who wants an actionable system redesign — not generic advice.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CONTEXT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Role        : {workflow['role']}
Industry    : {workflow['industry']}
Tools in use: {', '.join(workflow['tools_used']) or 'None specified'}
Pain points : {', '.join(workflow['pain_points']) or 'None specified'}
Total weekly work: {analysis['total_weekly_hours']}h across {len(analysis['classified_tasks'])} tasks

CURRENT TASKS (pre-classified by rule engine):
{tasks_block}

PRE-IDENTIFIED INEFFICIENCIES (do NOT repeat these verbatim):
{ineff_block}

PRE-CALCULATED ROI:
  • Time recoverable/week : {roi['time_saved_per_week']}h
  • Efficiency gain       : {roi['efficiency_gain_percent']}%
  • Automation score      : {roi['automation_score']}/100
  • Annual hours saved    : {roi['annual_hours_saved']}h

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
YOUR OUTPUT — Follow this exact structure. No extra sections.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## SECTION 3 — AUTOMATION OPPORTUNITIES
For EACH task listed above, provide:
  - Exact tool or method (name it specifically, e.g. "Make.com scenario", "Claude Projects", "Buffer calendar")
  - Implementation complexity: Easy / Medium / Hard
  - Expected outcome in one sentence

## SECTION 4 — OPTIMISED WORKFLOW
Redesign the entire weekly workflow for this specific {workflow['role']} in {workflow['industry']}.
  - Give a day-by-day or time-block structure
  - Name every tool explicitly
  - Show how tasks connect (output of one feeds next)
  - Total redesigned time should be ≤ {roi['hours_remaining_per_week']}h/week

## SECTION 5 — IMPLEMENTATION PLAN
Numbered steps (max 10). Each step must include:
  - What to do (specific action, not category)
  - Estimated setup time (e.g. "2 hours")
  - What it unlocks

## SECTION 7 — EXECUTIVE SUMMARY
4 sentences maximum.
  1. What the current workflow costs them (time + opportunity)
  2. What the biggest single change is
  3. What they gain after 30 days of implementation
  4. The one action to take TODAY

RULES:
  - Every tool mentioned must be real and available in 2025
  - No bullet walls — max 6 bullets per section, use prose where possible
  - Do NOT repeat the inefficiencies section (already provided above)
  - Tailor every recommendation to {workflow['role']} in {workflow['industry']}
  - Be direct. No hedging. No "consider" or "you might want to"."""

    return prompt


# ── API caller ─────────────────────────────────────────────────────────────────

def _call_deepseek(prompt: str) -> Optional[str]:
    """
    Send prompt to DeepSeek and return the response text.
    Returns None on any failure (network, auth, timeout).
    """
    try:
        client = _get_client()
        response = client.chat.completions.create(
            model=DEEPSEEK_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a senior AI workflow consultant. "
                        "You write structured, actionable audits. "
                        "Follow the output format exactly as specified. "
                        "Be specific — never generic."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            max_tokens=MAX_TOKENS,
            temperature=TEMPERATURE,
            stream=False,
        )
        return response.choices[0].message.content
    except EnvironmentError as e:
        print(f"[AI Engine] Config error: {e}")
        return None
    except Exception as e:
        print(f"[AI Engine] API call failed ({type(e).__name__}): {e}")
        return None


# ── Fallback generator ─────────────────────────────────────────────────────────

def _generate_fallback_content(analysis: Dict, roi: Dict) -> str:
    """
    Deterministic fallback for sections 3, 4, 5, 7 when DeepSeek is unavailable.
    Produces a complete, usable report section — not placeholder text.
    """
    workflow = analysis["input"]
    opps = analysis.get("automation_opportunities", [])
    classified = analysis["classified_tasks"]
    top_repetitive = [ct["task"] for ct in classified if ct["category"] == "repetitive"][:2]
    tools = workflow.get("tools_used", [])

    opps_lines = "\n".join(
        f"- **{o['task']}** → {o['automation_suggestion']}  "
        f"*(Priority: {o['priority']} | Est. {o['estimated_hours_saved']:.1f}h/week saved)*"
        for o in opps
    )

    repetitive_str = ", ".join(top_repetitive) if top_repetitive else "repetitive tasks"
    tools_str = ", ".join(tools) if tools else "your current tools"

    return f"""## SECTION 3 — AUTOMATION OPPORTUNITIES

{opps_lines}

> *Connect your DeepSeek API key for tool-specific automation blueprints tailored to {workflow['role']} in {workflow['industry']}.*

---

## SECTION 4 — OPTIMISED WORKFLOW

**Redesigned weekly system for {workflow['role']} ({workflow['industry']}):**

1. **Monday — Planning block (30 min):** Review priorities in Notion/ClickUp. Set weekly outputs. No task switching after this.
2. **Daily — Batch creative work (AM block):** All content creation in one focused session. Use AI for first drafts.
3. **Daily — Automated distribution:** Scheduled posts/emails fire automatically via Buffer or Make.com. No manual publish.
4. **Daily — Communication block (30 min, fixed time):** Reply to comments, emails, DMs in one batch. Not on-demand.
5. **Weekly — Review + repurpose (Friday, 1h):** Audit what worked. Feed top content into new formats with AI.

Total redesigned time target: **{roi['hours_remaining_per_week']:.1f}h/week** (down from {roi['total_hours_per_week']:.1f}h).

---

## SECTION 5 — IMPLEMENTATION PLAN

1. **Set up .env with DeepSeek API key** — 10 min — Unlocks full AI analysis in future runs
2. **Audit your {tools_str} integrations** — 1h — Identify what can be connected via Zapier/Make.com
3. **Automate {repetitive_str}** — 2–3h setup — Removes the biggest weekly time drain immediately
4. **Create AI content templates** — 1h — Drafts in minutes, not hours; consistency across all output
5. **Set up a content scheduler** — 30 min — Buffer or native platform scheduling; posts go out automatically
6. **Build a single Notion dashboard** — 1h — One hub for tasks, content calendar, and metrics
7. **Document your new workflow as an SOP** — 1h — Turns your system into a repeatable process
8. **Run Week 1 and measure actual time** — Ongoing — Compare against this audit; adjust where needed

---

## SECTION 7 — EXECUTIVE SUMMARY

Your current workflow consumes {roi['total_hours_per_week']:.1f}h/week across {len(classified)} tasks, with {roi['efficiency_gain_percent']}% of that time directly recoverable through automation and AI assistance. The single biggest lever is eliminating manual repetition from your highest-hour tasks — this alone reclaims {roi['time_saved_per_week']:.1f}h/week. After 30 days of implementation, you will have a systematised, partially automated operation running on {roi['hours_remaining_per_week']:.1f}h/week — freeing {roi['annual_hours_saved']:.0f} hours per year for growth work. **Start today:** pick your top repetitive task and set up one automation for it before end of day.

> *Note: Add your DEEPSEEK_API_KEY to .env for a fully personalised, role-specific analysis.*
"""


# ── Public entry point ─────────────────────────────────────────────────────────

def get_ai_analysis(analysis: Dict, roi: Dict) -> Dict:
    """
    Main AI engine entry point.
    Attempts DeepSeek API call; falls back to deterministic content on failure.

    Returns:
        {
            "success": bool,
            "content": str,   # Markdown sections 3, 4, 5, 7
            "model":   str,   # "deepseek-chat" or "fallback"
        }
    """
    prompt = build_analysis_prompt(analysis, roi)
    response = _call_deepseek(prompt)

    if response:
        return {"success": True, "content": response, "model": DEEPSEEK_MODEL}
    else:
        return {
            "success": False,
            "content": _generate_fallback_content(analysis, roi),
            "model": "fallback",
        }
