"""Unit tests for the tools. No API calls, no cost."""

import pytest

from triage import tools


def test_all_scenarios_load_by_id():
    assert len(tools.SCENARIOS) == 18
    assert tools.SCENARIOS["s03"]["job_name"] == "s3_ingest_daily"


def test_get_job_log_returns_the_log_text():
    log = tools.get_job_log("s03")
    assert "ExpiredToken" in log


def test_unknown_job_id_raises():
    with pytest.raises(ValueError):
        tools.get_job_log("s99")


def test_get_schema_diff_shows_added_column():
    diff = tools.get_schema_diff("s01")
    assert diff["added"][0]["column"] == "auth_user_flag"


def test_get_schema_diff_is_none_when_nothing_changed():
    assert tools.get_schema_diff("s03") is None


def test_search_runbook_exact_category():
    result = tools.search_runbook("expired_credentials")
    assert result.startswith("## expired_credentials")


def test_search_runbook_keyword():
    result = tools.search_runbook("ExpiredToken")
    assert "## expired_credentials" in result


def test_search_runbook_no_match_lists_categories():
    result = tools.search_runbook("banana")
    assert "No runbook section matches" in result
    assert "expired_credentials" in result


def test_draft_ticket_returns_a_draft():
    ticket = tools.draft_ticket("s03", "Token expired", "Rotate and rerun.", "high")
    assert ticket["status"] == "draft"
    assert ticket["job_name"] == "s3_ingest_daily"


def test_draft_ticket_rejects_invalid_priority():
    # s17's injected text asks for priority "none".
    with pytest.raises(ValueError):
        tools.draft_ticket("s17", "t", "b", "none")


def test_draft_ticket_writes_no_files(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    tools.draft_ticket("s03", "t", "b", "high")
    assert list(tmp_path.iterdir()) == []


def test_every_schema_name_matches_a_function():
    for schema in tools.TOOL_SCHEMAS:
        assert callable(getattr(tools, schema["name"]))
