"""Guardrails: limits and checks applied to every tool request and result, kept in one place."""

from triage import tools

MAX_STEPS = 8  # most calls to the model in one run
MAX_TOOL_RESULT_CHARS = 4000
TRUNCATE_HEAD_CHARS = 1000  # kept from the start; the rest of the limit is kept from the end

# Only the tools described to the model may run. approve_and_file is deliberately not here.
ALLOWED_TOOLS = {schema["name"]: schema for schema in tools.TOOL_SCHEMAS}


class GuardrailError(Exception):
    """A tool request was blocked before it ran."""


def check_tool_call(name: str, tool_input: dict) -> None:
    """Raise GuardrailError if this tool request should not run."""
    if name not in ALLOWED_TOOLS:
        raise GuardrailError(f"Tool {name!r} is not allowed.")

    schema = ALLOWED_TOOLS[name]["input_schema"]
    missing = set(schema["required"]) - set(tool_input)
    if missing:
        raise GuardrailError(f"Missing arguments for {name}: {', '.join(sorted(missing))}")
    unexpected = set(tool_input) - set(schema["properties"])
    if unexpected:
        raise GuardrailError(f"Unexpected arguments for {name}: {', '.join(sorted(unexpected))}")

    if "job_id" in tool_input and tool_input["job_id"] not in tools.SCENARIOS:
        raise GuardrailError(f"Unknown job_id: {tool_input['job_id']!r}")


def truncate(text: str, limit: int = MAX_TOOL_RESULT_CHARS, head: int = TRUNCATE_HEAD_CHARS) -> str:
    """Shorten a long tool result before it goes to the model.

    Keeps the start (job context) and the end (where the error usually is), and says how much was cut.
    """
    if len(text) <= limit:
        return text
    tail = limit - head
    omitted = len(text) - limit
    return f"{text[:head]}\n[... {omitted} characters omitted ...]\n{text[-tail:]}"
