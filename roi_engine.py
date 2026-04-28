"""
roi_engine.py — Deterministic ROI calculation for AI Workflow Auditor.
Pure maths. No external dependencies. No AI involvement.

Formulae:
  time_saved       = Σ (task_hours × reduction_factor)
  efficiency_gain  = (time_saved / total_hours) × 100
  automation_score = weighted average by category (0–100)
  annual_value     = time_saved × 52 × hourly_rate
"""

from typing import Dict, List


# ── Constants ──────────────────────────────────────────────────────────────────
WEEKS_PER_YEAR = 52
DEFAULT_HOURLY_VALUE = 50.0   # USD — overridable by user

# Automation score weights per category (how automatable is it?)
AUTOMATION_WEIGHTS: Dict[str, float] = {
    "repetitive":    1.00,
    "operational":   0.70,
    "creative":      0.40,
    "decision-based": 0.20,
}


# ── Core calculations ──────────────────────────────────────────────────────────

def calculate_time_saved(classified_tasks: List[Dict]) -> float:
    """
    Sum of (hours × reduction_factor) across all tasks.
    Returns hours saved per week.
    """
    return round(sum(ct["time_saved"] for ct in classified_tasks), 2)


def calculate_efficiency_gain(time_saved: float, total_hours: float) -> float:
    """
    Percentage efficiency improvement.
    Returns 0.0 if total_hours is zero (avoids division by zero).
    """
    if total_hours == 0:
        return 0.0
    return round((time_saved / total_hours) * 100, 1)


def calculate_automation_score(classified_tasks: List[Dict]) -> int:
    """
    Weighted automation score from 0 to 100.
    Weighted by hours (heavier tasks influence score more).
    Score = (Σ hours × weight) / (Σ hours × 1.0) × 100
    """
    if not classified_tasks:
        return 0

    total_hours = sum(ct["hours"] for ct in classified_tasks)
    if total_hours == 0:
        return 0

    weighted_sum = sum(
        ct["hours"] * AUTOMATION_WEIGHTS.get(ct["category"], 0.5)
        for ct in classified_tasks
    )

    score = (weighted_sum / total_hours) * 100
    return min(100, max(0, round(score)))


def calculate_annual_value(time_saved_per_week: float, hourly_value: float) -> float:
    """
    Estimated annual monetary value of time recovered.
    Formula: time_saved × 52 weeks × hourly_rate
    """
    return round(time_saved_per_week * WEEKS_PER_YEAR * hourly_value, 2)


def get_category_breakdown(classified_tasks: List[Dict]) -> Dict[str, Dict]:
    """
    Aggregate totals per category.
    Returns dict keyed by category with task count, total hours, hours saved.
    """
    breakdown: Dict[str, Dict] = {}
    for ct in classified_tasks:
        cat = ct["category"]
        if cat not in breakdown:
            breakdown[cat] = {"tasks": 0, "total_hours": 0.0, "hours_saved": 0.0}
        breakdown[cat]["tasks"] += 1
        breakdown[cat]["total_hours"] = round(
            breakdown[cat]["total_hours"] + ct["hours"], 2
        )
        breakdown[cat]["hours_saved"] = round(
            breakdown[cat]["hours_saved"] + ct["time_saved"], 2
        )
    return breakdown


# ── Master ROI engine ──────────────────────────────────────────────────────────

def run_roi_engine(
    analysis: Dict, hourly_value: float = DEFAULT_HOURLY_VALUE
) -> Dict:
    """
    Main ROI engine entry point.
    Accepts the analysis dict from processor.process_workflow().
    Returns a complete ROI report dict.

    Args:
        analysis:     Output of processor.process_workflow()
        hourly_value: The user's estimated hourly rate in USD (default $50)

    Returns:
        Dict with keys:
          time_saved_per_week, total_hours_per_week, efficiency_gain_percent,
          automation_score, annual_value_usd, annual_hours_saved,
          hours_remaining_per_week, hourly_value_used, category_breakdown
    """
    classified = analysis["classified_tasks"]
    total_hours = analysis["total_weekly_hours"]

    time_saved = calculate_time_saved(classified)
    efficiency_gain = calculate_efficiency_gain(time_saved, total_hours)
    automation_score = calculate_automation_score(classified)
    annual_value = calculate_annual_value(time_saved, hourly_value)
    breakdown = get_category_breakdown(classified)

    return {
        "time_saved_per_week":      time_saved,
        "total_hours_per_week":     total_hours,
        "efficiency_gain_percent":  efficiency_gain,
        "automation_score":         automation_score,
        "annual_value_usd":         annual_value,
        "annual_hours_saved":       round(time_saved * WEEKS_PER_YEAR, 1),
        "hours_remaining_per_week": round(total_hours - time_saved, 2),
        "hourly_value_used":        hourly_value,
        "category_breakdown":       breakdown,
    }
