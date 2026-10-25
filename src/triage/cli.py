"""Triage one job from the terminal: python -m triage.cli <job_id>

Filing a ticket needs a human. approve_and_file asks y/n here, and it is not a model tool.
"""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from triage.agent import print_run, run_triage
from triage.tools import SCENARIOS

# Stand-in for a real ticketing system such as ServiceNow.
TICKETS_FILE = Path(__file__).resolve().parents[2] / "out" / "tickets.jsonl"


def approve_and_file(draft: dict, ask=input, tickets_file: Path = TICKETS_FILE) -> bool:
    """Show a draft ticket, ask the human y/n, and write it only on yes. Returns True if filed."""
    print("\nDraft ticket:")
    print(json.dumps(draft, indent=2))
    try:
        answer = ask("File this ticket? [y/N]: ").strip().lower()
    except EOFError:  # no keyboard attached (a script or CI): treat as "no"
        answer = ""
    if answer not in ("y", "yes"):
        print("Not filed.")
        return False

    ticket = {**draft, "status": "filed", "filed_at": datetime.now(timezone.utc).isoformat()}
    tickets_file.parent.mkdir(parents=True, exist_ok=True)
    with open(tickets_file, "a", encoding="utf-8") as f:
        f.write(json.dumps(ticket) + "\n")
    print(f"Filed to {tickets_file}")
    return True


def main(args: list[str]) -> int:
    """Returns the exit code: 0 for success, non-zero for a usage problem."""
    if len(args) != 1:
        print("Usage: python -m triage.cli <job_id>")
        return 2
    job_id = args[0]
    # Check before calling the model, so a typo costs nothing.
    if job_id not in SCENARIOS:
        print(f"Unknown job id: {job_id!r}. Known ids: {', '.join(SCENARIOS)}")
        return 1

    run = run_triage(job_id)
    print_run(run)
    if not run["drafts"]:
        print("\nNo ticket drafted.")
    for draft in run["drafts"]:
        approve_and_file(draft)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
