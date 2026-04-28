"""
processor.py -- Deterministic task classification and inefficiency detection.
Zero AI dependency. All logic is rule-based and reproducible.
"""

from typing import Dict, List


# -- Classification keyword maps --
# Priority order: decision -> repetitive -> creative -> operational
# Repetitive checked before creative so "Schedule posts" hits 'schedule'
# before 'post', giving the correct higher reduction factor.

DECISION_KEYWORDS = [
    "analyse", "analyze", "analysis", "decide", "decision", "evaluate",
    "assess", "assessment", "research", "audit", "negotiate", "pitch",
    "present", "forecast", "budget", "invest", "strategy", "strategise",
    "strategize", "plan",
]

REPETITIVE_KEYWORDS = [
    "schedule", "scheduling", "reply", "replies", "respond", "send",
    "upload", "download", "update", "check", "follow up",
    "follow-up", "data entry", "fill", "format", "convert", "compile",
    "collect", "track", "monitor", "log", "invoice", "email",
    "paste", "export", "import", "publish", "repost", "reshare",
    "tag", "comment", "distribute", "automate", "batch",
]

CREATIVE_KEYWORDS = [
    "write", "writing", "draft", "design", "create", "content", "produce",
    "film", "record", "edit", "illustrate", "compose", "craft", "generate",
    "brainstorm", "ideate", "build", "develop", "concept", "article",
    "post", "script", "copy", "graphic", "thumbnail",
]

OPERATIONAL_KEYWORDS = [
    "manage", "coordinate", "organise", "organize", "meet", "meeting",
    "call", "interview", "onboard", "train", "support", "handle",
    "process", "approve", "delegate", "assign", "prioritise", "prioritize",
    "review", "oversee", "supervise",
]

# Reduction factors (midpoints of documented ranges)
REDUCTION_FACTORS = {
    "repetitive":     0.65,   # 50-80% reducible
    "creative":       0.20,   # 10-30% assistable
    "operational":    0.45,   # 30-60% reducible
    "decision-based": 0.15,   # 10-20% assistable
}

FRAGMENTATION_THRESHOLD = 3
HIGH_REPETITIVE_HOURS   = 5.0
MID_OPERATIONAL_HOURS   = 4.0

_NO_SYSTEM_SIGNALS = [
    "no system", "no process", "no workflow", "disorganised",
    "disorganized", "manual", "ad hoc", "ad-hoc", "inconsistent",
]

_KNOWN_AI_TOOLS = [
    "chatgpt", "claude", "gpt", "openai", "gemini", "copilot",
    "midjourney", "dalle", "dall-e", "jasper", "writesonic", "ai",
]

_AUTOMATION_MAP = {
    "repetitive": [
        "Use Make.com or Zapier to automate triggers and data flows",
        "Batch and schedule with Buffer, Hootsuite, or platform-native schedulers",
        "Build AI-powered templates for recurring output (Claude/ChatGPT)",
        "Set up auto-responders or trained AI agents for routine replies",
    ],
    "creative": [
        "Use Claude or ChatGPT for first drafts -- edit, don't write from scratch",
        "Canva AI + brand templates for consistent visual design",
        "Repurpose one long-form piece into 5+ formats with AI",
        "Use AI to generate hooks, CTAs, and variations in bulk",
    ],
    "operational": [
        "Create SOPs in Notion or ClickUp -- document once, run forever",
        "Use Calendly or Cal.com to eliminate scheduling back-and-forth",
        "Delegate routine coordination to a VA or AI scheduling agent",
        "Time-block all operational tasks into one daily power hour",
    ],
    "decision-based": [
        "Use AI (Perplexity, Claude) for research synthesis and summarisation",
        "Build decision dashboards in Notion or Airtable for at-a-glance status",
        "Automate recurring reports so analysis is ready without manual pull",
        "Use AI to generate options + pros/cons frameworks before deciding",
    ],
}

_PRIORITY_MAP = {
    "repetitive":     "HIGH",
    "operational":    "MEDIUM",
    "creative":       "MEDIUM",
    "decision-based": "LOW",
}


# -- Task classifier --

def classify_task(task_name):
    """
    Classify a task into one of four categories using keyword matching.
    Priority order: decision-based > repetitive > creative > operational.
    Falls back to 'operational' when no keyword matches.
    """
    lower = task_name.lower()

    for kw in DECISION_KEYWORDS:
        if kw in lower:
            return "decision-based"

    for kw in REPETITIVE_KEYWORDS:
        if kw in lower:
            return "repetitive"

    for kw in CREATIVE_KEYWORDS:
        if kw in lower:
            return "creative"

    for kw in OPERATIONAL_KEYWORDS:
        if kw in lower:
            return "operational"

    return "operational"


def classify_all_tasks(workflow):
    """Classify every task and return an enriched list with category, reduction factor, time saved."""
    classified = []
    for task in workflow["tasks"]:
        category  = classify_task(task["task"])
        hours     = float(task["time_per_week_hours"])
        reduction = REDUCTION_FACTORS[category]
        classified.append({
            "task":             task["task"],
            "hours":            hours,
            "category":         category,
            "reduction_factor": reduction,
            "time_saved":       round(hours * reduction, 2),
        })
    return classified


# -- Inefficiency detector --

def detect_inefficiencies(workflow):
    """
    Apply rule-based inefficiency detection.
    Returns a deduplicated list of dicts: task, reason, impact, severity, rule.
    """
    inefficiencies = []
    classified  = workflow.get("classified_tasks", [])
    tools       = workflow.get("tools_used", [])
    pain_points = workflow.get("pain_points", [])

    # Rule 1: High-time repetitive tasks
    for ct in classified:
        if ct["category"] == "repetitive" and ct["hours"] >= 2.0:
            severity = "HIGH" if ct["hours"] >= HIGH_REPETITIVE_HOURS else "MEDIUM"
            inefficiencies.append({
                "task":     ct["task"],
                "reason":   (
                    "Repetitive task consuming {:.1f}h/week -- "
                    "prime candidate for full or partial automation".format(ct["hours"])
                ),
                "impact":   (
                    "Est. {:.1f}h/week recoverable "
                    "({:.0f}% reduction factor)".format(ct["time_saved"], ct["reduction_factor"] * 100)
                ),
                "severity": severity,
                "rule":     "repetitive_time_{}".format(ct["task"][:20]),
            })

    # Rule 2: Tool fragmentation
    if len(tools) >= FRAGMENTATION_THRESHOLD:
        inefficiencies.append({
            "task":     "Cross-tool workflow",
            "reason":   (
                "{} separate tools in use ({}) without documented integration -- "
                "context-switching and manual data transfer overhead".format(
                    len(tools), ", ".join(tools)
                )
            ),
            "impact":   (
                "Estimated 1-{}h/week lost to tool-switching "
                "and copy-pasting between platforms".format(len(tools) - 1)
            ),
            "severity": "HIGH" if len(tools) > 4 else "MEDIUM",
            "rule":     "tool_fragmentation",
        })

    # Rule 3: Heavy operational overhead
    for ct in classified:
        if ct["category"] == "operational" and ct["hours"] >= MID_OPERATIONAL_HOURS:
            inefficiencies.append({
                "task":     ct["task"],
                "reason":   (
                    "Operational task at {:.1f}h/week -- "
                    "partially automatable with templates, scheduling tools, or delegation".format(ct["hours"])
                ),
                "impact":   (
                    "Est. {:.1f}h/week reducible "
                    "({:.0f}% reduction factor)".format(ct["time_saved"], ct["reduction_factor"] * 100)
                ),
                "severity": "MEDIUM",
                "rule":     "operational_overhead_{}".format(ct["task"][:20]),
            })

    # Rule 4: Pain points indicating no system
    for pp in pain_points:
        if any(sig in pp.lower() for sig in _NO_SYSTEM_SIGNALS):
            inefficiencies.append({
                "task":     "Overall system",
                "reason":   (
                    "Pain point flagged: '{}' -- "
                    "indicates absence of a documented workflow or SOP".format(pp)
                ),
                "impact":   (
                    "Without a system, all tasks are subject to inconsistency, "
                    "rework, and mental overhead"
                ),
                "severity": "HIGH",
                "rule":     "no_system",
            })
            break

    # Rule 5: Creative work with no AI tools
    creative_tasks = [ct for ct in classified if ct["category"] == "creative"]
    tools_lower    = [t.lower() for t in tools]
    has_ai         = any(ai in t for t in tools_lower for ai in _KNOWN_AI_TOOLS)

    if creative_tasks and not has_ai:
        total_creative = sum(ct["hours"] for ct in creative_tasks)
        inefficiencies.append({
            "task":     "Creative tasks",
            "reason":   (
                "{} creative task(s) detected "
                "but no AI writing or design tools in current stack".format(len(creative_tasks))
            ),
            "impact":   (
                "Est. {:.1f}h/week assistable "
                "with AI (Claude, ChatGPT, Canva AI, etc.)".format(total_creative * 0.20)
            ),
            "severity": "MEDIUM",
            "rule":     "no_ai_creative",
        })

    # Deduplicate on rule tag
    seen   = set()
    unique = []
    for item in inefficiencies:
        if item["rule"] not in seen:
            seen.add(item["rule"])
            unique.append(item)

    return unique


# -- Automation opportunities --

def get_automation_opportunities(classified_tasks):
    """Generate one targeted automation suggestion per task, sorted by priority."""
    opportunities = []
    for ct in classified_tasks:
        category      = ct["category"]
        suggestions   = _AUTOMATION_MAP.get(category, _AUTOMATION_MAP["operational"])
        idx           = 0 if ct["hours"] >= 5 else (1 if ct["hours"] >= 3 else 2)
        idx           = min(idx, len(suggestions) - 1)

        opportunities.append({
            "task":                   ct["task"],
            "category":               category,
            "hours":                  ct["hours"],
            "automation_suggestion":  suggestions[idx],
            "priority":               _PRIORITY_MAP[category],
            "estimated_hours_saved":  ct["time_saved"],
        })

    priority_order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
    return sorted(opportunities, key=lambda x: priority_order[x["priority"]])


# -- Master processor --

def process_workflow(workflow):
    """
    Main entry point. Accepts a validated + sanitized workflow dict.
    Returns an enriched analysis dict ready for the ROI engine and AI layer.
    """
    classified         = classify_all_tasks(workflow)
    workflow_enriched  = dict(workflow)
    workflow_enriched["classified_tasks"] = classified

    inefficiencies = detect_inefficiencies(workflow_enriched)
    opportunities  = get_automation_opportunities(classified)
    total_hours    = round(sum(ct["hours"] for ct in classified), 2)

    return {
        "input":                  workflow,
        "classified_tasks":       classified,
        "total_weekly_hours":     total_hours,
        "inefficiencies":         inefficiencies,
        "automation_opportunities": opportunities,
    }
