"""Tools the agent can call, plus their JSON schemas.

All tools read synthetic data from the data/ folder. None of them write anything.
"""

import json
from pathlib import Path

# src/triage/tools.py -> parents[2] is the project root.
DATA_DIR = Path(__file__).resolve().parents[2] / "data"


def load_scenarios(path: Path = DATA_DIR / "scenarios.json") -> dict[str, dict]:
    """Read scenarios.json and return a dict keyed by scenario id, e.g. {"s01": {...}}."""
    with open(path, encoding="utf-8") as f:
        scenarios = json.load(f)
    return {s["id"]: s for s in scenarios}


# Loaded once when this module is imported, then shared by every tool.
SCENARIOS = load_scenarios()


def _get_scenario(job_id: str) -> dict:
    """Look up one scenario, with a clear error for an unknown id."""
    if job_id not in SCENARIOS:
        raise ValueError(f"Unknown job_id: {job_id!r}")
    return SCENARIOS[job_id]


def get_job_log(job_id: str) -> str:
    """Return the log text for one job."""
    return _get_scenario(job_id)["log"]


def get_schema_diff(job_id: str) -> dict | None:
    """Return the schema changes for one job, or None if nothing changed."""
    return _get_scenario(job_id)["schema_diff"]


def load_runbook(path: Path = DATA_DIR / "runbook.md") -> dict[str, str]:
    """Split runbook.md into sections keyed by their ## heading, e.g. {"schema_drift": "## schema_drift\\n..."}."""
    text = path.read_text(encoding="utf-8")
    sections = {}
    # Everything before the first "## " is the page title, so skip it.
    for chunk in text.split("\n## ")[1:]:
        heading = chunk.split("\n", 1)[0].strip()
        sections[heading] = "## " + chunk.strip()
    return sections


# Loaded once, like SCENARIOS.
RUNBOOK = load_runbook()


def search_runbook(query: str) -> str:
    """Return the section for a category name, or every section containing a keyword."""
    q = query.strip()
    if q in RUNBOOK:
        return RUNBOOK[q]
    matches = [section for section in RUNBOOK.values() if q and q.lower() in section.lower()]
    if matches:
        return "\n\n".join(matches)
    return f"No runbook section matches {query!r}. Categories: {', '.join(RUNBOOK)}"


PRIORITIES = ("low", "medium", "high")


def draft_ticket(job_id: str, title: str, body: str, priority: str) -> dict:
    """Build a ticket draft. Saves and sends nothing; filing needs human approval in the CLI."""
    scenario = _get_scenario(job_id)
    if priority not in PRIORITIES:
        raise ValueError(f"Invalid priority: {priority!r}. Use one of: {', '.join(PRIORITIES)}")
    return {
        "status": "draft",
        "job_id": job_id,
        "job_name": scenario["job_name"],
        "title": title,
        "body": body,
        "priority": priority,
    }
