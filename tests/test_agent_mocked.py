"""Tests for the agent loop with a fake model client. No API calls, no cost.

The fake client returns scripted replies, so we can make the "model" misbehave on purpose.
"""

from types import SimpleNamespace

from triage import agent

VALID_JSON = (
    '{"category": "expired_credentials", "severity": "high", "root_cause": "Token expired.", '
    '"evidence": ["ExpiredToken"], "recommended_action": "Rotate and rerun.", "needs_human": false}'
)


def text_reply(text):
    """A fake model reply with no tool requests: the model's final answer."""
    return SimpleNamespace(stop_reason="end_turn", content=[SimpleNamespace(type="text", text=text)])


def tool_reply(name, tool_input):
    """A fake model reply asking for one tool."""
    block = SimpleNamespace(type="tool_use", id="toolu_test", name=name, input=tool_input)
    return SimpleNamespace(stop_reason="tool_use", content=[block])


class FakeClient:
    """Stands in for anthropic.Anthropic(). Returns the scripted replies in order and records each request."""

    def __init__(self, replies):
        self.replies = list(replies)
        self.requests = []
        self.messages = self  # so that client.messages.create(...) works

    def create(self, **kwargs):
        self.requests.append(list(kwargs["messages"]))  # copy, since the loop keeps adding to the list
        return self.replies.pop(0)


def test_valid_answer_after_a_tool_call():
    client = FakeClient([tool_reply("get_job_log", {"job_id": "s03"}), text_reply(VALID_JSON)])
    run = agent.run_triage("s03", client=client)
    assert run["ended"] == "valid"
    assert run["steps"] == 2
    assert run["result"].prompt_version == agent.PROMPT_VERSION


def test_invalid_answer_is_retried_once_with_the_error():
    client = FakeClient([text_reply("not json"), text_reply(VALID_JSON)])
    run = agent.run_triage("s03", client=client)
    assert run["ended"] == "valid"
    # The second request ends with our message telling the model what was wrong.
    assert "failed validation" in client.requests[1][-1]["content"]


def test_invalid_answer_twice_returns_fallback():
    client = FakeClient([text_reply("not json"), text_reply('{"category": "banana"}')])
    run = agent.run_triage("s03", client=client)
    assert run["ended"] == "fallback_invalid_output"
    assert run["result"].category == "unknown"
    assert run["result"].needs_human is True


def test_step_cap_returns_fallback_without_a_ninth_call():
    client = FakeClient([tool_reply("get_job_log", {"job_id": "s03"})] * agent.MAX_STEPS)
    run = agent.run_triage("s03", client=client)
    assert run["ended"] == "fallback_step_cap"
    assert len(client.requests) == agent.MAX_STEPS


def test_disallowed_tool_is_blocked_and_never_runs():
    client = FakeClient([tool_reply("approve_and_file", {"job_id": "s03"}), text_reply(VALID_JSON)])
    run = agent.run_triage("s03", client=client)
    assert run["log"][0]["blocked"] is True
    tool_result = client.requests[1][-1]["content"][0]
    assert tool_result["content"].startswith("Blocked by guardrail")


def test_tool_error_is_sent_back_to_the_model():
    # Passes the guardrails (all arguments present), but draft_ticket itself rejects priority "none".
    ticket = {"job_id": "s17", "title": "t", "body": "b", "priority": "none"}
    client = FakeClient([tool_reply("draft_ticket", ticket), text_reply(VALID_JSON)])
    run = agent.run_triage("s17", client=client)
    assert run["log"][0]["is_error"] is True
    assert run["log"][0]["blocked"] is False
    tool_result = client.requests[1][-1]["content"][0]
    assert tool_result["is_error"] is True
    assert "Invalid priority" in tool_result["content"]
