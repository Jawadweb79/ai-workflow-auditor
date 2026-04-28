"""
main.py — CLI entry point for AI Workflow Auditor.

Usage:
  python main.py              # Interactive CLI prompts
  python main.py --file input.json   # Load from JSON file
  python main.py --demo              # Run LinkedIn Creator sample data
  python main.py --demo --hourly 75  # Override hourly rate for ROI
"""

import argparse
import sys
import os
from dotenv import load_dotenv

# Load .env before importing ai_engine (which reads env vars)
load_dotenv()

from input_handler import collect_from_cli, load_from_file, load_from_dict
from processor import process_workflow
from roi_engine import run_roi_engine
from ai_engine import get_ai_analysis
from report_generator import generate_and_save_reports
from validator import ValidationError

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "reports")

# ── Demo input (LinkedIn Creator sample from spec) ────────────────────────────
DEMO_INPUT = {
    "role": "LinkedIn Creator",
    "industry": "Personal Branding",
    "tasks": [
        {"task": "Write posts manually",  "time_per_week_hours": 10},
        {"task": "Design content",        "time_per_week_hours": 5},
        {"task": "Schedule posts",        "time_per_week_hours": 3},
        {"task": "Reply to comments",     "time_per_week_hours": 4},
    ],
    "tools_used": ["ChatGPT", "Canva"],
    "pain_points": ["time consuming", "no system"],
}


# ── CLI summary printer ────────────────────────────────────────────────────────

def print_summary(analysis: dict, roi: dict) -> None:
    """Print a concise audit snapshot to the terminal."""
    w = analysis["input"]
    div = "=" * 62

    print(f"\n{div}")
    print("  AUDIT COMPLETE — RESULTS SNAPSHOT")
    print(div)
    print(f"\n  Role     : {w['role']}")
    print(f"  Industry : {w['industry']}")
    print(f"\n  📋 Tasks analysed    : {len(analysis['classified_tasks'])}")
    print(f"  ⏱  Total weekly time : {analysis['total_weekly_hours']:.1f}h")
    print(f"  ⚠  Inefficiencies    : {len(analysis['inefficiencies'])}")
    print(f"\n  ── ROI SNAPSHOT ───────────────────────────────────")
    print(f"  Time saved / week   : {roi['time_saved_per_week']:.1f}h")
    print(f"  Efficiency gain     : {roi['efficiency_gain_percent']}%")
    print(f"  Automation score    : {roi['automation_score']} / 100")
    print(f"  Annual hours saved  : {roi['annual_hours_saved']:.0f}h")
    print(f"  Annual value        : ${roi['annual_value_usd']:,.0f}")
    print()


# ── Audit pipeline ─────────────────────────────────────────────────────────────

def run_audit(workflow_data: dict, hourly_value: float = 50.0) -> None:
    """
    Execute the full four-stage audit pipeline:
      1. Process (classify + detect inefficiencies)
      2. ROI engine (deterministic calculation)
      3. AI layer (DeepSeek analysis or fallback)
      4. Report generation (MD + PDF)
    """
    print("\n  [1/4] Processing workflow — classifying tasks & detecting inefficiencies...")
    analysis = process_workflow(workflow_data)

    print(f"  [2/4] ROI engine — calculating time savings and automation score...")
    roi = run_roi_engine(analysis, hourly_value=hourly_value)

    print(f"  [3/4] AI analysis — calling DeepSeek...")
    ai_content = get_ai_analysis(analysis, roi)
    status = "✅ AI analysis complete" if ai_content["success"] else "⚠️  AI unavailable — deterministic fallback used"
    print(f"         {status}")

    print(f"  [4/4] Generating reports — Markdown + PDF...")
    paths = generate_and_save_reports(analysis, roi, ai_content, OUTPUT_DIR)

    print_summary(analysis, roi)

    print("  📄 REPORTS SAVED:")
    if paths.get("markdown"):
        print(f"     Markdown : {paths['markdown']}")
    if paths.get("pdf"):
        print(f"     PDF      : {paths['pdf']}")
    else:
        print("     PDF      : skipped (install reportlab to enable)")
    print()


# ── Entry point ────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="AI Workflow Auditor — diagnose, optimise, and quantify your workflow ROI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py                       # interactive prompts
  python main.py --demo                # run LinkedIn Creator sample
  python main.py --file my_input.json  # load from JSON file
  python main.py --demo --hourly 100   # custom hourly rate
        """,
    )
    parser.add_argument("--file",   "-f",  help="Path to JSON workflow input file")
    parser.add_argument("--demo",          help="Run with LinkedIn Creator sample data", action="store_true")
    parser.add_argument("--hourly", "-r",  help="Your hourly rate in USD for ROI calc (default: 50)", type=float, default=50.0)
    args = parser.parse_args()

    try:
        if args.demo:
            print("\n  🚀 Running with LinkedIn Creator demo data...")
            workflow = load_from_dict(DEMO_INPUT)
        elif args.file:
            print(f"\n  📂 Loading input from: {args.file}")
            workflow = load_from_file(args.file)
        else:
            workflow = collect_from_cli()

        run_audit(workflow, hourly_value=args.hourly)

    except ValidationError as e:
        print(f"\n  ❌ Validation Error:\n{e}\n")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n\n  Audit cancelled by user.")
        sys.exit(0)


if __name__ == "__main__":
    main()
