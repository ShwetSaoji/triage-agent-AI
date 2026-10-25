"""Unit tests for the guardrails. No API calls, no cost."""

import pytest

from triage.guardrails import GuardrailError, check_tool_call, truncate


def test_valid_call_passes():
    check_tool_call("get_job_log", {"job_id": "s03"})  # no error means it passed


def test_unknown_tool_is_blocked():
    with pytest.raises(GuardrailError):
        check_tool_call("delete_table", {"job_id": "s03"})


def test_approve_and_file_is_not_a_tool():
    # Filing needs a human in the CLI. The model must never be able to call it.
    with pytest.raises(GuardrailError):
        check_tool_call("approve_and_file", {"job_id": "s03"})


def test_unknown_job_id_is_blocked():
    with pytest.raises(GuardrailError):
        check_tool_call("get_job_log", {"job_id": "s99"})


def test_missing_argument_is_blocked():
    with pytest.raises(GuardrailError):
        check_tool_call("draft_ticket", {"job_id": "s03", "title": "t"})


def test_unexpected_argument_is_blocked():
    with pytest.raises(GuardrailError):
        check_tool_call("get_job_log", {"job_id": "s03", "delete": True})


def test_short_result_is_unchanged():
    assert truncate("short log") == "short log"


def test_long_result_keeps_start_and_end():
    # Real logs usually fail at the end, so the error line must survive truncation.
    log = "START job" + "x" * 10_000 + "ERROR: disk full"
    result = truncate(log, limit=4000, head=1000)
    assert result.startswith("START job")
    assert result.endswith("ERROR: disk full")
    assert "characters omitted" in result
