"""Talks to the model. For now (build step 3): one tool call and one tool result, printed. No loop yet."""

import json
import os
import sys
from pathlib import Path

import anthropic

from triage import tools

PROMPTS_DIR = Path(__file__).resolve().parents[2] / "prompts"
PROMPT_VERSION = "triage_v1"
MODEL = os.environ.get("TRIAGE_MODEL", "claude-sonnet-5-5")

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


def print_blocks(response) -> None:
    print(f"stop_reason: {response.stop_reason}")
    for block in response.content:
        if block.type == "text":
            print(f"  [text] {block.text}")
        elif block.type == "tool_use":
            print(f"  [tool_use] id={block.id} name={block.name} input={block.input}")
        else:
            print(f"  [{block.type}] (not shown)")


def first_call_demo(job_id: str) -> None:
    client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY from the environment
    system = load_system_prompt()
    messages = [{"role": "user", "content": f"Triage job {job_id}"}]

    print(f"=== Call 1: model={MODEL}, prompt={PROMPT_VERSION} ===")
    response = client.messages.create(
        model=MODEL, max_tokens=16000, system=system, tools=tools.TOOL_SCHEMAS, messages=messages
    )
    print_blocks(response)

    tool_uses = [block for block in response.content if block.type == "tool_use"]
    if not tool_uses:
        print("The model did not ask for a tool.")
        return

    # Send back the model's full turn, then one tool_result per tool_use, matched by id.
    messages.append({"role": "assistant", "content": response.content})
    results = []
    for tool_use in tool_uses:
        output = run_tool(tool_use.name, tool_use.input)
        print(f"\n=== Our code ran {tool_use.name} ===\n{output}")
        results.append({"type": "tool_result", "tool_use_id": tool_use.id, "content": output})
    messages.append({"role": "user", "content": results})

    print("\n=== Call 2: same conversation plus the tool result ===")
    response = client.messages.create(
        model=MODEL, max_tokens=16000, system=system, tools=tools.TOOL_SCHEMAS, messages=messages
    )
    print_blocks(response)


if __name__ == "__main__":
    first_call_demo(sys.argv[1] if len(sys.argv) > 1 else "s03")
