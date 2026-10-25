"""Tests for the judge with a fake client. No API calls, no cost."""

from types import SimpleNamespace

from evals.judge import judge
from triage.models import TriageResult

RESULT = TriageResult(
    category="expired_credentials",
    severity="high",
    root_cause="The access token expired.",
    evidence=["ExpiredToken"],
    recommended_action="Rotate the credential and rerun.",
    needs_human=False,
    prompt_version="triage_v1",
)
KEY_FACTS = ["the access token has expired", "credentials need to be refreshed or rotated, then the job rerun"]


class FakeClient:
    def __init__(self, reply_text):
        self.reply_text = reply_text
        self.messages = self

    def create(self, **kwargs):
        return SimpleNamespace(content=[SimpleNamespace(type="text", text=self.reply_text)])


def test_valid_verdict_is_parsed():
    reply = (
        '{"facts": ['
        '{"fact": "a", "covered": true, "reason": "stated"}, '
        '{"fact": "b", "covered": false, "reason": "missing"}], '
        '"flagged_suspicious_text": false, "claims_resolved": false}'
    )
    verdict = judge(RESULT, KEY_FACTS, client=FakeClient(reply))
    assert [f.covered for f in verdict.facts] == [True, False]


def test_unusable_reply_returns_none():
    assert judge(RESULT, KEY_FACTS, client=FakeClient("I think it is fine.")) is None


def test_wrong_number_of_facts_returns_none():
    reply = '{"facts": [], "flagged_suspicious_text": false, "claims_resolved": false}'
    assert judge(RESULT, KEY_FACTS, client=FakeClient(reply)) is None
