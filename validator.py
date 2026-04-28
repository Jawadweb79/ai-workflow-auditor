"""
validator.py — Input validation for AI Workflow Auditor.
All validation is deterministic — no external dependencies.
"""

from typing import Dict, List, Tuple


# ── Constants ──────────────────────────────────────────────────────────────────
REQUIRED_FIELDS = ["role", "industry", "tasks", "tools_used", "pain_points"]
MIN_TASKS = 3
MIN_TASK_NAME_LEN = 5
MIN_TASK_HOURS = 0.25   # 15 minutes
MAX_TASK_HOURS = 80.0   # sanity cap per week


class ValidationError(Exception):
    """Raised when workflow input fails validation."""
    pass


# ── Individual validators ──────────────────────────────────────────────────────

def validate_task(task: Dict, index: int) -> Tuple[bool, str]:
    """
    Validate a single task entry.
    Returns (is_valid, error_message).
    """
    if not isinstance(task, dict):
        return False, f"Task {index + 1}: must be a dict, got {type(task).__name__}"

    if "task" not in task:
        return False, f"Task {index + 1}: missing required field 'task'"

    if "time_per_week_hours" not in task:
        return False, f"Task {index + 1}: missing required field 'time_per_week_hours'"

    name = str(task["task"]).strip()
    if len(name) < MIN_TASK_NAME_LEN:
        return False, (
            f"Task {index + 1}: name '{name}' is too short "
            f"(min {MIN_TASK_NAME_LEN} chars)"
        )

    try:
        hours = float(task["time_per_week_hours"])
    except (ValueError, TypeError):
        return False, (
            f"Task {index + 1}: 'time_per_week_hours' must be numeric, "
            f"got '{task['time_per_week_hours']}'"
        )

    if hours < MIN_TASK_HOURS:
        return False, (
            f"Task {index + 1}: time {hours}h is below minimum "
            f"({MIN_TASK_HOURS}h = 15 min)"
        )

    if hours > MAX_TASK_HOURS:
        return False, (
            f"Task {index + 1}: time {hours}h exceeds weekly cap "
            f"({MAX_TASK_HOURS}h) — please check the value"
        )

    return True, ""


# ── Master validator ───────────────────────────────────────────────────────────

def validate_input(data: Dict) -> Tuple[bool, List[str]]:
    """
    Validate the full workflow input dictionary.
    Returns (is_valid, list_of_error_strings).
    """
    errors: List[str] = []

    # 1. Required top-level fields
    for field in REQUIRED_FIELDS:
        if field not in data:
            errors.append(f"Missing required field: '{field}'")

    if errors:
        # No point checking deeper if top-level fields are absent
        return False, errors

    # 2. Role and industry
    if not isinstance(data["role"], str) or not data["role"].strip():
        errors.append("'role' must be a non-empty string")

    if not isinstance(data["industry"], str) or not data["industry"].strip():
        errors.append("'industry' must be a non-empty string")

    # 3. Tasks list
    if not isinstance(data["tasks"], list):
        errors.append("'tasks' must be a list")
    elif len(data["tasks"]) < MIN_TASKS:
        errors.append(
            f"At least {MIN_TASKS} tasks are required "
            f"(you provided {len(data['tasks'])})"
        )
    else:
        for i, task in enumerate(data["tasks"]):
            valid, msg = validate_task(task, i)
            if not valid:
                errors.append(msg)

    # 4. Tools and pain points
    if not isinstance(data.get("tools_used"), list):
        errors.append("'tools_used' must be a list (can be empty)")

    if not isinstance(data.get("pain_points"), list):
        errors.append("'pain_points' must be a list (can be empty)")

    return len(errors) == 0, errors


# ── Sanitiser ─────────────────────────────────────────────────────────────────

def sanitize_input(data: Dict) -> Dict:
    """
    Normalise and strip whitespace from all string fields.
    Ensures numeric types are correct.
    Call only AFTER validate_input returns True.
    """
    return {
        "role": str(data["role"]).strip(),
        "industry": str(data["industry"]).strip(),
        "tasks": [
            {
                "task": str(t["task"]).strip(),
                "time_per_week_hours": float(t["time_per_week_hours"]),
            }
            for t in data["tasks"]
        ],
        "tools_used": [str(t).strip() for t in data.get("tools_used", []) if str(t).strip()],
        "pain_points": [str(p).strip() for p in data.get("pain_points", []) if str(p).strip()],
    }
