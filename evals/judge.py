"""LLM-as-judge: a second model call that grades whether the agent's explanation covers the key facts.

Used only for what plain code cannot check. The judge is a model too, so it can be wrong;
spot-check a sample of its verdicts by hand.
"""

import json
import os
from pathlib import Path

import anthropic
from pydantic import BaseModel

from triage.models import TriageResult, extract_json

PROMPTS_DIR = Path(__file__).resolve().parents[1] / "prompts"
JUDGE_PROMPT_VERSION = "judge_v1"
JUDGE_MODEL = os.environ.get("JUDGE_MODEL", "claude-sonnet-5-5")


class FactVerdict(BaseModel):
    fact: str
    covered: bool
    reason: str


class JudgeVerdict(BaseModel):
    facts: list[FactVerdict]
    flagged_suspicious_text: bool
    claims_resolved: bool


def judge(result: TriageResult, key_facts: list[str], client=None) -> JudgeVerdict | None:
    """Grade one triage result. Returns None if the judge's own reply is unusable."""
    client = client or anthropic.Anthropic()
    system = (PROMPTS_DIR / f"{JUDGE_PROMPT_VERSION}.md").read_text(encoding="utf-8")
    answer = result.model_dump(include={"root_cause", "evidence", "recommended_action"})
    user_message = (
        f"Key facts:\n{json.dumps(key_facts, indent=2)}\n\n"
        f"Agent answer to grade:\n<answer>\n{json.dumps(answer, indent=2)}\n</answer>"
    )
    response = client.messages.create(
        model=JUDGE_MODEL, max_tokens=16000, system=system, messages=[{"role": "user", "content": user_message}]
    )
    text = "".join(block.text for block in response.content if block.type == "text")
    try:
        verdict = JudgeVerdict.model_validate(extract_json(text))
    except ValueError:
        return None
    # One verdict per key fact, or the scores would not line up.
    if len(verdict.facts) != len(key_facts):
        return None
    return verdict
