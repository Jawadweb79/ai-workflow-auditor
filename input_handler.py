"""
input_handler.py — Workflow input collection and loading.
Supports three modes:
  1. load_from_file()  — JSON file on disk
  2. load_from_dict()  — Python dict (used by Streamlit UI)
  3. collect_from_cli() — interactive terminal prompts
"""

import json
from typing import Dict

from validator import validate_input, sanitize_input, ValidationError


# ── File loader ────────────────────────────────────────────────────────────────

def load_from_file(filepath: str) -> Dict:
    """
    Load, validate, and sanitize workflow input from a JSON file.
    Raises ValidationError on any problem.
    """
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        raise ValidationError(f"File not found: {filepath}")
    except json.JSONDecodeError as e:
        raise ValidationError(f"Invalid JSON in '{filepath}': {e}")

    return load_from_dict(data)


# ── Dict loader (used by Streamlit) ───────────────────────────────────────────

def load_from_dict(data: Dict) -> Dict:
    """
    Validate and sanitize a workflow input dict.
    Raises ValidationError with a formatted message on failure.
    """
    is_valid, errors = validate_input(data)
    if not is_valid:
        formatted = "\n".join(f"  • {e}" for e in errors)
        raise ValidationError(f"Input validation failed:\n{formatted}")
    return sanitize_input(data)


# ── Interactive CLI collector ──────────────────────────────────────────────────

def collect_from_cli() -> Dict:
    """
    Interactively prompt the user for workflow data via the terminal.
    Returns a validated and sanitized input dict.
    """
    print("\n" + "=" * 62)
    print("  AI WORKFLOW AUDITOR — Input Collection")
    print("=" * 62)

    # Role and industry
    print()
    role = input("Your role / job title : ").strip()
    industry = input("Your industry         : ").strip()

    # Tasks
    print(
        "\nEnter your weekly tasks (minimum 3). "
        "Type 'done' when finished.\n"
    )
    tasks = []
    while True:
        idx = len(tasks) + 1
        task_name = input(f"  Task {idx} name (or 'done'): ").strip()

        if task_name.lower() == "done":
            if len(tasks) < 3:
                print(f"  ⚠  Minimum 3 tasks required. You have {len(tasks)}. Continue adding.\n")
                continue
            break

        if not task_name:
            print("  Task name cannot be empty. Try again.\n")
            continue

        # Hours input — retry until numeric
        while True:
            raw = input(f"  Hours/week for '{task_name}': ").strip()
            try:
                hours = float(raw)
                if hours <= 0:
                    print("  Must be a positive number.")
                    continue
                break
            except ValueError:
                print("  Please enter a number (e.g. 3 or 1.5).")

        tasks.append({"task": task_name, "time_per_week_hours": hours})
        print()

    # Tools
    print("Tools you currently use (comma-separated, e.g. ChatGPT, Notion):")
    tools_raw = input("  Tools: ").strip()
    tools = [t.strip() for t in tools_raw.split(",") if t.strip()] if tools_raw else []

    # Pain points
    print("\nMain pain points (comma-separated, e.g. too manual, no system):")
    pain_raw = input("  Pain points: ").strip()
    pain_points = [p.strip() for p in pain_raw.split(",") if p.strip()] if pain_raw else []

    data = {
        "role": role,
        "industry": industry,
        "tasks": tasks,
        "tools_used": tools,
        "pain_points": pain_points,
    }

    # Final validation pass
    return load_from_dict(data)
