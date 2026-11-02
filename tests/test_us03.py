"""
Automated tests for US03 — Student takes a quiz with countdown timer.

Three test cases:

  TC-US03-01  normal     — a valid start creates a fresh attempt with the
                            correct remaining time and no saved answers
  TC-US03-02  error      — a student already taking one quiz is refused
                            when they start a second one           (BR1)
  TC-US03-03  boundary   — `save_answer` refuses past the time limit and
                            accepts before it; checks the BR3 boundary
                            on both sides of `time_limit_min * 60`

Every test runs WITHOUT a real database and WITHOUT a running server:
the repository and lease layer inside `attempt_service` are monkeypatched
with canned values from mock_data_us03.py.

Run from the repository root:

    python -m pytest test/test_us03.py -v
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

from src.models.attempt import SaveAnswerRequest
from src.services.attempt_service import (
    start_attempt,
    save_answer,
    ConflictError,
)

import mock_data_us03


DEVICE_ID = "test-device-abcdef"


# ----------------------------------------------------------------------
# Fakes — nothing here talks to PostgreSQL
# ----------------------------------------------------------------------

class _FakeConn:
    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        return False


class _FakeLease:
    """A lease manager that always says 'you own it'."""

    def __init__(self):
        self.acquired = 0

    def acquire(self, attempt_id, device_id, force=False):
        self.acquired += 1
        return True, device_id

    def release(self, attempt_id, device_id):
        return True

    def force_release(self, attempt_id):
        pass


def _patch_common(monkeypatch):
    """Patches needed by every US03 test: DB connect + role lookup + lease."""
    monkeypatch.setattr(
        "src.services.attempt_service.db_config.connect",
        lambda: _FakeConn(),
    )
    monkeypatch.setattr(
        "src.services.attempt_service.repo.get_user_role_status",
        lambda conn, email: mock_data_us03.ACTIVE_STUDENT_ROW,
    )

    lease = _FakeLease()
    monkeypatch.setattr(
        "src.services.attempt_service.lease_manager",
        lease,
    )
    return lease


# ----------------------------------------------------------------------
# TC-US03-01 — normal case
# ----------------------------------------------------------------------

def test_tc_us03_01_start_fresh_attempt(monkeypatch):
    """
    TC-US03-01 · US03 · normal

    A Student with no active attempt starts a published quiz.

    Expect:
      * AttemptState with remaining_seconds = time_limit_min * 60
      * no saved answers yet
      * flagged = False
      * the MCQ question carries 4 options; the SHORT question carries none
    """
    _patch_common(monkeypatch)

    monkeypatch.setattr(
        "src.services.attempt_service.repo.list_expired_attempts",
        lambda conn, student_id: [],
    )
    monkeypatch.setattr(
        "src.services.attempt_service.repo.get_quiz_header",
        lambda conn, quiz_id: mock_data_us03.quiz_header(quiz_id=quiz_id),
    )
    monkeypatch.setattr(
        "src.services.attempt_service.repo.get_active_attempt_id",
        lambda conn, student_id, quiz_id: None,
    )
    monkeypatch.setattr(
        "src.services.attempt_service.repo.get_any_active_attempt",
        lambda conn, student_id: None,
    )
    monkeypatch.setattr(
        "src.services.attempt_service.repo.is_active_enrolled",
        lambda conn, student_id, course_id: True,
    )
    monkeypatch.setattr(
        "src.services.attempt_service.repo.list_questions_for_attempt",
        lambda conn, quiz_id: mock_data_us03.question_rows(),
    )
    monkeypatch.setattr(
        "src.services.attempt_service.repo.insert_attempt",
        lambda conn, quiz_id, student_id: 100,
    )
    monkeypatch.setattr(
        "src.services.attempt_service.repo.get_attempt_full",
        lambda conn, attempt_id: mock_data_us03.attempt_row(
            attempt_id=attempt_id,
            quiz_id=1,
            time_limit_min=30,
            elapsed_seconds=0,   # just started
        ),
    )
    monkeypatch.setattr(
        "src.services.attempt_service.repo.list_options_for_attempt",
        lambda conn, qid: mock_data_us03.MCQ_OPTIONS if qid == 101 else [],
    )
    monkeypatch.setattr(
        "src.services.attempt_service.repo.list_answers_for_attempt",
        lambda conn, attempt_id: [],
    )

    result = start_attempt("minhhd@univ.edu", quiz_id=1, device_id=DEVICE_ID)

    assert result.attempt_id == 100
    assert result.quiz_id == 1
    assert result.quiz_title == "ACC101 Midterm Quiz"
    assert result.course_code == "ACC101"
    assert result.time_limit_min == 30
    assert result.remaining_seconds == 30 * 60   # 1800
    assert result.tab_switch_count == 0
    assert result.flagged is False

    assert len(result.questions) == 2
    assert result.questions[0].question_type == "MCQ"
    assert len(result.questions[0].options) == 4
    assert result.questions[1].question_type == "SHORT"
    assert result.questions[1].options == []

    assert result.saved_answers == []


# ----------------------------------------------------------------------
# TC-US03-02 — error case
# ----------------------------------------------------------------------

def test_tc_us03_02_cannot_start_second_quiz(monkeypatch):
    """
    TC-US03-02 · US03 · error

    A Student who already has an active attempt on quiz #2 tries to
    start quiz #1. The service must refuse with a ConflictError and
    return the active quiz's id/title in the `extra` payload so the
    client can offer a "Resume active quiz" button (BR1).
    """
    _patch_common(monkeypatch)

    monkeypatch.setattr(
        "src.services.attempt_service.repo.list_expired_attempts",
        lambda conn, student_id: [],
    )
    monkeypatch.setattr(
        "src.services.attempt_service.repo.get_quiz_header",
        lambda conn, quiz_id: mock_data_us03.quiz_header(quiz_id=quiz_id),
    )
    monkeypatch.setattr(
        "src.services.attempt_service.repo.get_active_attempt_id",
        lambda conn, student_id, quiz_id: None,   # no active on THIS quiz
    )
    monkeypatch.setattr(
        "src.services.attempt_service.repo.get_any_active_attempt",
        lambda conn, student_id: mock_data_us03.OTHER_ACTIVE_ATTEMPT,
    )

    # Track whether insert_attempt is ever called — it must NOT be.
    insert_calls = []
    monkeypatch.setattr(
        "src.services.attempt_service.repo.insert_attempt",
        lambda *args, **kwargs: insert_calls.append(args) or 100,
    )

    with pytest.raises(ConflictError) as exc_info:
        start_attempt("minhhd@univ.edu", quiz_id=1, device_id=DEVICE_ID)

    err = exc_info.value
    assert "already have an active attempt" in err.message
    assert err.status_code == 409
    # The client needs this to offer "Resume active quiz":
    assert err.extra["active_quiz_id"] == 2
    assert err.extra["active_attempt_id"] == 99
    # Nothing was created:
    assert insert_calls == []


# ----------------------------------------------------------------------
# TC-US03-03 — boundary case on both sides of BR3 (time limit)
# ----------------------------------------------------------------------

@pytest.mark.parametrize(
    "elapsed_seconds, should_succeed",
    [
        pytest.param(1799, True,  id="TC-US03-03a-below-limit"),   # 1s left
        pytest.param(1800, False, id="TC-US03-03b-at-limit"),      # 00:00
        pytest.param(1801, False, id="TC-US03-03c-above-limit"),   # 1s over
    ],
)
def test_tc_us03_03_save_answer_at_time_boundary(
    monkeypatch, elapsed_seconds, should_succeed
):
    """
    TC-US03-03 · US03 · boundary (BR3)

    BR3: the quiz auto-submits when the timer reaches 00:00 — i.e. once
    `elapsed_seconds` reaches `time_limit_min * 60` (here: 30 * 60 = 1800).

    A `save_answer` call is checked on both sides of that boundary:

        1799s elapsed → succeeds, answer is persisted
        1800s elapsed → 409 "Time has expired. Submitting now."
        1801s elapsed → 409 "Time has expired. Submitting now."
    """
    _patch_common(monkeypatch)

    monkeypatch.setattr(
        "src.services.attempt_service.repo.get_attempt_full",
        lambda conn, attempt_id: mock_data_us03.attempt_row(
            attempt_id=100,
            quiz_id=1,
            time_limit_min=30,
            elapsed_seconds=elapsed_seconds,
        ),
    )
    # Only used on the success path — harmless to leave in place:
    monkeypatch.setattr(
        "src.services.attempt_service.repo.get_question_in_quiz",
        lambda conn, qid, quiz_id: mock_data_us03.single_mcq_question_row(),
    )
    monkeypatch.setattr(
        "src.services.attempt_service.repo.get_option_in_question",
        lambda conn, oid, qid: mock_data_us03.SINGLE_MCQ_OPTION_ROW,
    )

    upsert_calls = []
    monkeypatch.setattr(
        "src.services.attempt_service.repo.upsert_answer",
        lambda *args, **kwargs: upsert_calls.append(args),
    )

    payload = SaveAnswerRequest(
        device_id=DEVICE_ID,
        chosen_option_id=1001,
        text_answer=None,
    )

    if should_succeed:
        save_answer("minhhd@univ.edu", attempt_id=100, question_id=101, payload=payload)
        assert len(upsert_calls) == 1
        # Confirm nothing was silently dropped:
        args = upsert_calls[0]
        assert args[1] == 100   # attempt_id
        assert args[2] == 101   # question_id
        assert args[3] == 1001  # chosen_option_id
    else:
        with pytest.raises(ConflictError) as exc_info:
            save_answer(
                "minhhd@univ.edu", attempt_id=100, question_id=101, payload=payload,
            )
        assert "Time has expired" in exc_info.value.message
        assert exc_info.value.status_code == 409
        # Nothing was persisted:
        assert upsert_calls == []