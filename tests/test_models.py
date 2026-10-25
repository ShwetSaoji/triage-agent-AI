"""Unit tests for the output schema and parsing. No API calls, no cost."""

import pytest

from triage.models import fallback, parse_result

VALID_JSON = (
    '{"category": "expired_credentials", "severity": "high", "root_cause": "Token expired.", '
    '"evidence": ["ExpiredToken"], "recommended_action": "Rotate and rerun.", "needs_human": false}'
)


def test_parses_json_wrapped_in_markdown_fences():
    result = parse_result(f"```json\n{VALID_JSON}\n```", "triage_v1")
    assert result.category == "expired_credentials"
    assert result.prompt_version == "triage_v1"


def test_our_prompt_version_overwrites_the_models():
    text = VALID_JSON.replace("}", ', "prompt_version": "made_up"}')
    assert parse_result(text, "triage_v1").prompt_version == "triage_v1"


def test_rejects_invalid_severity():
    with pytest.raises(ValueError):
        parse_result(VALID_JSON.replace('"high"', '"critical"'), "triage_v1")


def test_rejects_text_with_no_json():
    with pytest.raises(ValueError):
        parse_result("I could not decide.", "triage_v1")


def test_fallback_is_valid_and_asks_for_a_human():
    result = fallback("step cap reached", "triage_v1")
    assert result.category == "unknown"
    assert result.needs_human is True
