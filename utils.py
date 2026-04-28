"""
utils.py — Shared utility functions for AI Workflow Auditor.
Keep this module dependency-free (stdlib only).
"""

import json
import os
from datetime import datetime
from typing import Any, Dict


def load_json(filepath: str) -> Dict:
    """Load and return a JSON file as a dict."""
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(data: Dict, filepath: str) -> None:
    """Serialise data to a JSON file with pretty indentation."""
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def get_timestamp() -> str:
    """Return a filesystem-safe timestamp string: YYYY-MM-DD_HH-MM-SS."""
    return datetime.now().strftime("%Y-%m-%d_%H-%M-%S")


def get_date() -> str:
    """Return today's date as YYYY-MM-DD."""
    return datetime.now().strftime("%Y-%m-%d")


def ensure_dir(path: str) -> None:
    """Create directory (and parents) if it doesn't already exist."""
    os.makedirs(path, exist_ok=True)


def format_hours(hours: float) -> str:
    """Return a human-readable duration string from a float hour value."""
    if hours < 1:
        return f"{int(hours * 60)} min"
    elif hours == int(hours):
        return f"{int(hours)}h"
    else:
        return f"{hours:.1f}h"


def clamp(value: float, min_val: float, max_val: float) -> float:
    """Clamp a value between min_val and max_val (inclusive)."""
    return max(min_val, min(max_val, value))


def bold(text: str) -> str:
    """Wrap text in markdown bold markers."""
    return f"**{text}**"
