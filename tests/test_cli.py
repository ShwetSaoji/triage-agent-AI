"""Tests for the CLI approval step. No API calls, no cost, no real keyboard."""

import json

from triage.cli import approve_and_file, main

DRAFT = {
    "status": "draft",
    "job_id": "s03",
    "job_name": "s3_ingest_daily",
    "title": "Expired token",
    "body": "Rotate and rerun.",
    "priority": "high",
}


def test_yes_files_exactly_one_ticket(tmp_path):
    tickets = tmp_path / "tickets.jsonl"
    assert approve_and_file(DRAFT, ask=lambda prompt: "y", tickets_file=tickets) is True
    lines = tickets.read_text().splitlines()
    assert len(lines) == 1
    assert json.loads(lines[0])["status"] == "filed"


def test_no_files_nothing(tmp_path):
    tickets = tmp_path / "tickets.jsonl"
    assert approve_and_file(DRAFT, ask=lambda prompt: "n", tickets_file=tickets) is False
    assert not tickets.exists()


def test_pressing_enter_files_nothing(tmp_path):
    # The safe choice is the default: an accidental Enter never files a ticket.
    tickets = tmp_path / "tickets.jsonl"
    assert approve_and_file(DRAFT, ask=lambda prompt: "", tickets_file=tickets) is False
    assert not tickets.exists()


def test_no_keyboard_files_nothing(tmp_path):
    def no_keyboard(prompt):
        raise EOFError

    tickets = tmp_path / "tickets.jsonl"
    assert approve_and_file(DRAFT, ask=no_keyboard, tickets_file=tickets) is False
    assert not tickets.exists()


def test_unknown_job_id_stops_before_calling_the_model():
    assert main(["s3"]) == 1
