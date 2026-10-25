"""The agent loop: call the model, run the tools it asks for, repeat until it gives a final answer."""

import json
import os
import sys
from pathlib import Path

import anthropic

from triage import tools
from triage.guardrails import MAX_STEPS, GuardrailError, check_tool_call, truncate
from triage.models import fallback, parse_result

PROMPTS_DIR = Path(__file__).resolve().parents[2] / "prompts"
PROMPT_VERSION = "triage_v1"
MODEL = os.environ.get("TRIAGE_MODEL", "claude-sonnet-5-5")
LOG_PREVIEW_CHARS = 300

# Maps the tool name the model asks for to the Python function that runs it.
TOOL_FUNCTIONS = {
    "get_job_log": tools.get_job_log,
    "get_schema_diff": tools.get_schema_diff,
    "search_runbook": tools.search_runbook,
    "draft_ticket": tools.draft_ticket,
}


def load_system_prompt(version: str = PROMPT_VERSION) -> str:
    return (PROMPTS_DIR / f"{version}.md").read_text(encoding="utf-8")


def run_tool(name: str, tool_input: dict) -> str:
    """Run one tool and return its result as text, which is what the API expects back."""
    result = TOOL_FUNCTIONS[name](**tool_input)
    return result if isinstance(result, str) else json.dumps(result)


def _preview(text: str) -> str:
    """Shorten long text for the log."""
    return text if len(text) <= LOG_PREVIEW_CHARS else text[:LOG_PREVIEW_CHARS] + "..."


def run_triage(job_id: str, client=None) -> dict:
    """Investigate one job. Always returns a valid TriageResult, how the run ended, and a log of every step.

    Pass a fake client in tests so no real API call is made.
    """
    client = client or anthropic.Anthropic()  # reads ANTHROPIC_API_KEY from the environment
    system = load_system_prompt()
    messages = [{"role": "user", "content": f"Triage job {job_id}"}]
    log = []
    retried = False

    for step in range(1, MAX_STEPS + 1):
        response = client.messages.create(
            model=MODEL, max_tokens=16000, system=system, tools=tools.TOOL_SCHEMAS, messages=messages
        )

        # No tool requests means the model is giving its final answer. Check it.
        if response.stop_reason != "tool_use":
            final_text = "".join(block.text for block in response.content if block.type == "text")
            try:
                result = parse_result(final_text, PROMPT_VERSION)
                log.append({"step": step, "event": "valid_answer"})
                return {"result": result, "ended": "valid", "steps": step, "log": log}
            except ValueError as error:
                log.append({"step": step, "event": "invalid_answer", "error": _preview(str(error))})
                if retried:
                    result = fallback("the answer failed validation twice", PROMPT_VERSION)
                    return {"result": result, "ended": "fallback_invalid_output", "steps": step, "log": log}
                # First failure: show the model the exact error and give it one more turn.
                retried = True
                messages.append({"role": "assistant", "content": response.content})
                messages.append({
                    "role": "user",
                    "content": f"Your answer failed validation:\n{error}\nReply with only the corrected JSON object.",
                })
                continue

        messages.append({"role": "assistant", "content": response.content})
        results = []
        for block in response.content:
            if block.type != "tool_use":
                continue
            # Guardrails check the request before anything runs. A blocked or failing
            # tool is reported back to the model, so it can correct itself.
            blocked = False
            try:
                check_tool_call(block.name, block.input)
                output = truncate(run_tool(block.name, block.input))
                is_error = False
            except GuardrailError as error:
                output = f"Blocked by guardrail: {error}"
                is_error = blocked = True
            except Exception as error:
                output = f"Error: {error}"
                is_error = True
            log.append({
                "step": step,
                "event": "tool_call",
                "tool": block.name,
                "input": block.input,
                "result": _preview(output),
                "is_error": is_error,
                "blocked": blocked,
            })
            results.append({"type": "tool_result", "tool_use_id": block.id, "content": output, "is_error": is_error})
        messages.append({"role": "user", "content": results})

    log.append({"step": MAX_STEPS, "event": "step_cap_reached"})
    result = fallback(f"no valid answer within {MAX_STEPS} steps", PROMPT_VERSION)
    return {"result": result, "ended": "fallback_step_cap", "steps": MAX_STEPS, "log": log}


def print_run(run: dict) -> None:
    for entry in run["log"]:
        if entry["event"] == "tool_call":
            flag = "  (BLOCKED)" if entry["blocked"] else "  (ERROR)" if entry["is_error"] else ""
            print(f"Step {entry['step']}: {entry['tool']} {entry['input']}{flag}")
            print(f"    -> {entry['result'].replace(chr(10), ' | ')}")
        else:
            print(f"Step {entry['step']}: {entry['event']} {entry.get('error', '')}")
    print(f"\nEnded: {run['ended']} after {run['steps']} steps")
    print(f"Result:\n{run['result'].model_dump_json(indent=2)}")


if __name__ == "__main__":
    print_run(run_triage(sys.argv[1] if len(sys.argv) > 1 else "s03"))
