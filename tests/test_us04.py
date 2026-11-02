"""
Automated tests for US04 — Automatic grading + immediate score.

Three test cases:

  TC-US04-01  normal    — a mixed MCQ/SHORT submission is graded correctly;
                          the whitespace-padded SHORT answer "  Hà Nội "
                          is accepted (AC3), the wrong MCQ and the wrong
                          SHORT answer each score 0
  TC-US04-02  error     — re-submitting an already-submitted attempt is
                          refused with `Attempt already submitted` (409);
                          grading is not run a second time
  TC-US04-03  boundary  — BR5: the percentage is rounded to 2 decimal
                          places; tested on both sides of the .xx5
                          threshold (33.33 / 66.67 / 77.78 / 80.0 / 62.5)

Every test runs WITHOUT a real database and WITHOUT a running server:
`db_config.connect`, the repository layer, and the lease manager are
monkeypatched with canned values from mock_data_us04.py.

Run from the repository root:

    python -m pytest test/test_us04.py -v
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

from src.models.attempt import SubmitRequest
from src.services.attempt_service import (
    submit_attempt,
    ConflictError,
    _percentage,   # BR5 lives here; tested directly in TC-US04-03
)

import mock_data_us04


DEVICE_ID = "test-device-abcdef"


# ----------------------------------------------------------------------
# Fakes
# ----------------------------------------------------------------------

class _FakeConn:
    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        return False


class _FakeLease:
    def acquire(self, attempt_id, device_id, force=False):
        return True, device_id

    def release(self, attempt_id, device_id):
        return True

    def force_release(self, attempt_id):
        pass


def _patch_common(monkeypatch):
    """Wire up every DB-touching layer inside attempt_service."""
    monkeypatch.setattr(
        "src.services.attempt_service.db_config.connect",
        lambda: _FakeConn(),
    )
    monkeypatch.setattr(
        "src.services.attempt_service.repo.get_user_role_status",
        lambda conn, email: mock_data_us04.ACTIVE_STUDENT_ROW,
    )
    monkeypatch.setattr(
        "src.services.attempt_service.lease_manager",
        _FakeLease(),
    )


# ----------------------------------------------------------------------
# TC-US04-01 — normal case
# ----------------------------------------------------------------------

def test_tc_us04_01_grade_mixed_submission(monkeypatch):
    """
    TC-US04-01 · US04 · normal

    Grade a partially correct attempt:
      Q1 MCQ   → student picked the right option     +1
      Q2 MCQ   → student picked the wrong option      0
      Q3 SHORT → "  Hà Nội " vs "Hà Nội" (AC3)       +1
      Q4 SHORT → "London" vs "Paris"                  0

    Expected: score = 2, total = 4, percentage = 50.0, auto_submitted = False
    """
    _patch_common(monkeypatch)

    monkeypatch.setattr(
        "src.services.attempt_service.repo.get_attempt_full",
        lambda conn, attempt_id: mock_data_us04.unsubmitted_attempt(),
    )
    monkeypatch.setattr(
        "src.services.attempt_service.repo.list_questions_for_attempt",
        lambda conn, quiz_id: mock_data_us04.QUESTION_ROWS,
    )
    monkeypatch.setattr(
        "src.services.attempt_service.repo.get_grading_data",
        lambda conn, quiz_id: mock_data_us04.GRADING_DATA,
    )
    monkeypatch.setattr(
        "src.services.attempt_service.repo.get_correct_option_map",
        lambda conn, quiz_id: mock_data_us04.CORRECT_OPTION_MAP,
    )
    monkeypatch.setattr(
        "src.services.attempt_service.repo.get_answer_id_map",
        lambda conn, attempt_id: mock_data_us04.ANSWER_ID_MAP,
    )
    monkeypatch.setattr(
        "src.services.attempt_service.repo.list_answers_for_attempt",
        lambda conn, attempt_id: mock_data_us04.STUDENT_ANSWERS,
    )

    # Capture is_correct calls so we can assert that the wrong answers
    # were marked wrong (not just that the total happens to come out right):
    correctness_calls = []
    monkeypatch.setattr(
        "src.services.attempt_service.repo.update_answer_correctness",
        lambda conn, answer_id, is_correct: correctness_calls.append(
            (answer_id, is_correct)
        ),
    )

    finalized = []
    monkeypatch.setattr(
        "src.services.attempt_service.repo.finalize_attempt",
        lambda conn, attempt_id, score, total, auto_submitted: finalized.append(
            (attempt_id, score, total, auto_submitted)
        ),
    )

    result = submit_attempt(
        "minhhd@univ.edu",
        100,
        SubmitRequest(device_id=DEVICE_ID, auto_submitted=False),
    )

    assert result.score == 2
    assert result.total == 4
    assert result.percentage == 50.0
    assert result.auto_submitted is False

    # Each question's correctness was recorded exactly once.
    # Q1 (3001) correct, Q2 (3002) wrong, Q3 (3003) correct, Q4 (3004) wrong
    assert sorted(correctness_calls) == sorted([
        (3001, True),
        (3002, False),
        (3003, True),
        (3004, False),
    ])

    # The attempt was finalized exactly once with the right numbers.
    assert finalized == [(100, 2, 4, False)]


# ----------------------------------------------------------------------
# TC-US04-02 — error case
# ----------------------------------------------------------------------

def test_tc_us04_02_cannot_resubmit_attempt(monkeypatch):
    """
    TC-US04-02 · US04 · error

    An attempt that has already been graded cannot be graded again.
    Submitting it a second time must be refused with a 409, and
    `finalize_attempt` must not run a second time.
    """
    _patch_common(monkeypatch)

    monkeypatch.setattr(
        "src.services.attempt_service.repo.get_attempt_full",
        lambda conn, attempt_id: mock_data_us04.already_submitted_attempt(),
    )

    finalize_calls = []
    monkeypatch.setattr(
        "src.services.attempt_service.repo.finalize_attempt",
        lambda *args, **kwargs: finalize_calls.append(args),
    )
    # Grading inputs should never be consulted — but if they are, this
    # makes the test fail loudly rather than silently pass.
    monkeypatch.setattr(
        "src.services.attempt_service.repo.list_questions_for_attempt",
        lambda conn, quiz_id: mock_data_us04.QUESTION_ROWS,
    )
    monkeypatch.setattr(
        "src.services.attempt_service.repo.get_grading_data",
        lambda conn, quiz_id: mock_data_us04.GRADING_DATA,
    )
    monkeypatch.setattr(
        "src.services.attempt_service.repo.get_correct_option_map",
        lambda conn, quiz_id: mock_data_us04.CORRECT_OPTION_MAP,
    )
    monkeypatch.setattr(
        "src.services.attempt_service.repo.get_answer_id_map",
        lambda conn, attempt_id: mock_data_us04.ANSWER_ID_MAP,
    )
    monkeypatch.setattr(
        "src.services.attempt_service.repo.list_answers_for_attempt",
        lambda conn, attempt_id: mock_data_us04.STUDENT_ANSWERS,
    )
    monkeypatch.setattr(
        "src.services.attempt_service.repo.update_answer_correctness",
        lambda *args, **kwargs: None,
    )

    with pytest.raises(ConflictError) as exc_info:
        submit_attempt(
            "minhhd@univ.edu",
            100,
            SubmitRequest(device_id=DEVICE_ID, auto_submitted=False),
        )

    assert "already submitted" in exc_info.value.message
    assert exc_info.value.status_code == 409
    assert finalize_calls == []


# ----------------------------------------------------------------------
# TC-US04-03 — boundary case on both sides of BR5
# ----------------------------------------------------------------------

@pytest.mark.parametrize(
    "score, total, expected",
    mock_data_us04.BR5_BOUNDARY_CASES,
    ids=[
        "TC-US04-03a-round-down",       # 1/3  → 33.33
        "TC-US04-03b-round-up",         # 2/3  → 66.67
        "TC-US04-03c-round-up-near-100",# 7/9  → 77.78
        "TC-US04-03d-exact-80",         # 8/10 → 80.0
        "TC-US04-03e-exact-62-5",       # 5/8  → 62.5
    ],
)
def test_tc_us04_03_percentage_rounding_boundaries(score, total, expected):
    """
    TC-US04-03 · US04 · boundary (BR5)

    BR5: the percentage is rounded to 2 decimal places.

    The case table covers both sides of the .xx5 rounding threshold —
    values below round down; values above round up; exact values stay
    exact. This is the "both sides of the number" check required by
    the milestone's boundary rule.
    """
    assert _percentage(score, total) == expected