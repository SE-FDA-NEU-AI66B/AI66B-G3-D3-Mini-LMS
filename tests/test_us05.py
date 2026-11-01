"""
Automated tests for US05 — Lecturer publishes / unpublishes a quiz.

Three test cases:

  TC-US05-01  normal    — a Draft quiz with ≥1 question and a future
                          due date is published; status becomes
                          "Published" and the DB row is updated
  TC-US05-02  error     — a Draft quiz with no questions cannot be
                          published (422); status unchanged
  TC-US05-03  boundary  — due-date check on both sides of `_now_utc_naive()`:
                          1 s before now → refused
                          exactly at now → refused (the rule uses <=)
                          1 s after now  → accepted

Every test runs WITHOUT a real database and WITHOUT a running server:
`db_config.connect`, the repository layer, and `_now_utc_naive` are
monkeypatched with canned values from mock_data_us05.py.

Run from the repository root:

    python -m pytest test/test_us05.py -v
"""

from __future__ import annotations

import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

THIS_DIR = pathlib.Path(__file__).resolve().parent
if str(THIS_DIR) not in sys.path:
    sys.path.insert(0, str(THIS_DIR))

import pytest

from src.services.instructor_quiz_service import (
    publish_quiz,
    ValidationError,
)

import mock_data_us05


# ----------------------------------------------------------------------
# Fakes
# ----------------------------------------------------------------------

class _FakeConn:
    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        return False


def _patch_publish(
    monkeypatch,
    *,
    due_at,
    questions: list[tuple],
    initial_status: str = "Draft",
):
    """
    Wire up `publish_quiz` for a test.

    Returns a tuple `(state, calls)` where:
      * `state["status"]` reflects the current DB-side status, updated
        by `fake_set_status` so a second `get_quiz` call sees the new
        status the way the real DB would.
      * `calls["set_status"]` counts how many times
        `repo.set_quiz_status` was actually invoked — used by the error
        and boundary tests to prove nothing was written.
    """
    state = {"status": initial_status}
    calls = {"set_status": 0}

    monkeypatch.setattr(
        "src.services.instructor_quiz_service.db_config.connect",
        lambda: _FakeConn(),
    )
    monkeypatch.setattr(
        "src.services.instructor_quiz_service.repo.get_user_by_email",
        lambda conn, email: mock_data_us05.LECTURER_ROW,
    )
    monkeypatch.setattr(
        "src.services.instructor_quiz_service.quiz_repository.apply_scheduled_publishes",
        lambda conn: 0,
    )
    monkeypatch.setattr(
        "src.services.instructor_quiz_service._now_utc_naive",
        lambda: mock_data_us05.FIXED_NOW,
    )
    monkeypatch.setattr(
        "src.services.instructor_quiz_service.repo.get_quiz",
        lambda conn, qid: mock_data_us05.quiz_row(
            quiz_id=qid, due_at=due_at, status=state["status"],
        ),
    )
    monkeypatch.setattr(
        "src.services.instructor_quiz_service.repo.list_questions",
        lambda conn, qid: questions,
    )
    monkeypatch.setattr(
        "src.services.instructor_quiz_service.repo.list_options",
        lambda conn, qid: mock_data_us05.OPTION_ROWS,
    )

    def fake_set_status(conn, qid, new_status):
        calls["set_status"] += 1
        state["status"] = new_status

    monkeypatch.setattr(
        "src.services.instructor_quiz_service.repo.set_quiz_status",
        fake_set_status,
    )

    return state, calls


# ----------------------------------------------------------------------
# TC-US05-01 — normal case
# ----------------------------------------------------------------------

def test_tc_us05_01_publish_draft_quiz(monkeypatch):
    """
    TC-US05-01 · US05 · normal

    A Draft quiz that has one question and a far-future due date is
    published. The DB row's status becomes "Published" and the returned
    QuizDetail reflects the new status.
    """
    state, calls = _patch_publish(
        monkeypatch,
        due_at=mock_data_us05.DUE_FAR,
        questions=mock_data_us05.question_rows(),
        initial_status="Draft",
    )

    result = publish_quiz("lanpt@univ.edu", quiz_id=42)

    assert result.quiz_id == 42
    assert result.status == "Published"
    assert state["status"] == "Published"
    assert calls["set_status"] == 1
    # The quiz detail still carries the question the lecturer authored.
    assert len(result.questions) == 1
    assert result.questions[0].question_type == "MCQ"


# ----------------------------------------------------------------------
# TC-US05-02 — error case
# ----------------------------------------------------------------------

def test_tc_us05_02_cannot_publish_quiz_with_no_questions(monkeypatch):
    """
    TC-US05-02 · US05 · error

    A Draft quiz with zero questions cannot be published. The service
    raises ValidationError(422) before touching `set_quiz_status`, so
    the DB row stays Draft.
    """
    state, calls = _patch_publish(
        monkeypatch,
        due_at=mock_data_us05.DUE_FAR,
        questions=[],   # <-- the trigger
        initial_status="Draft",
    )

    with pytest.raises(ValidationError) as exc_info:
        publish_quiz("lanpt@univ.edu", quiz_id=42)

    assert "Cannot publish a quiz with no questions" in exc_info.value.message
    assert exc_info.value.status_code == 422
    # Nothing was written:
    assert state["status"] == "Draft"
    assert calls["set_status"] == 0


# ----------------------------------------------------------------------
# TC-US05-03 — boundary case on both sides of the due-date guard
# ----------------------------------------------------------------------

@pytest.mark.parametrize(
    "due_at, should_succeed",
    [
        pytest.param(mock_data_us05.DUE_PAST,   False, id="TC-US05-03a-past-due"),
        pytest.param(mock_data_us05.DUE_AT_NOW, False, id="TC-US05-03b-exactly-now"),
        pytest.param(mock_data_us05.DUE_FUTURE, True,  id="TC-US05-03c-just-future"),
    ],
)
def test_tc_us05_03_publish_due_date_boundary(monkeypatch, due_at, should_succeed):
    """
    TC-US05-03 · US05 · boundary (due date vs now)

    The service's guard is `if quiz_row[6] <= _now_utc_naive()` (the due
    date must be strictly after now). Tested on both sides of that
    boundary:

        FIXED_NOW - 1 s → refused
        FIXED_NOW       → refused  (<= is inclusive)
        FIXED_NOW + 1 s → accepted
    """
    state, calls = _patch_publish(
        monkeypatch,
        due_at=due_at,
        questions=mock_data_us05.question_rows(),
        initial_status="Draft",
    )

    if should_succeed:
        result = publish_quiz("lanpt@univ.edu", quiz_id=42)
        assert result.status == "Published"
        assert state["status"] == "Published"
        assert calls["set_status"] == 1
    else:
        with pytest.raises(ValidationError) as exc_info:
            publish_quiz("lanpt@univ.edu", quiz_id=42)
        assert "due date has passed" in exc_info.value.message
        assert exc_info.value.status_code == 422
        # Nothing was written:
        assert state["status"] == "Draft"
        assert calls["set_status"] == 0