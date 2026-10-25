"""The final output schema, plus helpers to read the model's answer and build a safe fallback."""

import json
from typing import Literal

from pydantic import BaseModel

Category = Literal[
    "schema_drift",
    "expired_credentials",
    "out_of_memory",
    "upstream_file_missing",
    "data_quality_threshold",
    "permission_denied",
    "dependency_timeout",
    "duplicate_load",
    "unknown",
]
Severity = Literal["low", "medium", "high"]


class TriageResult(BaseModel):
    category: Category
    severity: Severity
    root_cause: str
    evidence: list[str]
    recommended_action: str
    needs_human: bool
    prompt_version: str  # filled in by our code, never by the model


def parse_result(text: str, prompt_version: str) -> TriageResult:
    """Pull the JSON object out of the model's text and validate it.

    Raises ValueError if there is no valid JSON object or a field is wrong.
    (pydantic's ValidationError and json's JSONDecodeError are both kinds of ValueError.)
    """
    # Take everything from the first "{" to the last "}", which skips markdown fences or stray text.
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end < start:
        raise ValueError("No JSON object found in the answer.")
    data = json.loads(text[start : end + 1])
    data["prompt_version"] = prompt_version  # overwrite anything the model wrote here
    return TriageResult.model_validate(data)


def fallback(reason: str, prompt_version: str) -> TriageResult:
    """A safe result for when triage fails: unknown cause, a human must look."""
    return TriageResult(
        category="unknown",
        severity="medium",
        root_cause=f"Automated triage failed: {reason}",
        evidence=[],
        recommended_action="Investigate this job manually.",
        needs_human=True,
        prompt_version=prompt_version,
    )
