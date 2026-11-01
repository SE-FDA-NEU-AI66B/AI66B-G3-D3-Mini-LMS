"""
Automated tests for US01 — Lecturer creates a quiz (MCQ + short answer).

Three test cases:

  TC-US01-01  normal case   — a valid quiz is created as a Draft
  TC-US01-02  error case    — an empty title is rejected before any DB write
  TC-US01-03  boundary case — time_limit_min is accepted at [5, 120] and
                              rejected on both sides [4, 121]  (BR2)

Every test runs WITHOUT a real database and WITHOUT a running server:
the DB layer of `instructor_quiz_service` is monkeypatched with fake
functions that return the rows from `mock_data_us01.py`.

Run from the repository root:

    python -m pytest tests/test_us01.py -v
"""

from __future__ import annotations

import pathlib
import sys

# tests/ → repo root (two levels up)
ROOT = pathlib.Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# tests/ (own directory — used for `import mock_data_us01`)
THIS_DIR = pathlib.Path(__file__).resolve().parent
if str(THIS_DIR) not in sys.path:
    sys.path.insert(0, str(THIS_DIR))

import pytest

from src.models.quiz import QuizCreateRequest
from src.services.instructor_quiz_service import create_quiz, ValidationError

import mock_data_us01


# ----------------------------------------------------------------------
# Fakes — the only thing that touches the (non-existent) database
# ----------------------------------------------------------------------

class _FakeConn:
    """Stand-in for a psycopg connection — only used as a context manager."""

    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        return False


def _patch_db(monkeypatch, *, time_limit_min: int = 30):
    """
    Replace every DB-touching call inside `instructor_quiz_service` with
    a lambda that returns a canned row from `mock_data_us01`.

    After this returns, calling `create_quiz(...)` never opens a real
    socket or connects to PostgreSQL.
    """
    monkeypatch.setattr(
        "src.services.instructor_quiz_service.db_config.connect",
        lambda: _FakeConn(),
    )
    monkeypatch.setattr(
        "src.services.instructor_quiz_service.repo.get_user_by_email",
        lambda conn, email: mock_data_us01.LECTURER_ROW,
    )
    monkeypatch.setattr(
        "src.services.instructor_quiz_service.repo.get_course",
        lambda conn, course_id: mock_data_us01.COURSE_OWNED_ROW,
    )
    monkeypatch.setattr(
        "src.services.instructor_quiz_service.repo.insert_quiz",
        lambda *args, **kwargs: 42,
    )
    monkeypatch.setattr(
        "src.services.instructor_quiz_service.repo.get_quiz",
        lambda conn, qid: mock_data_us01.quiz_row(time_limit_min=time_limit_min),
    )
    monkeypatch.setattr(
        "src.services.instructor_quiz_service.repo.list_questions",
        lambda conn, qid: [],
    )
    monkeypatch.setattr(
        "src.services.instructor_quiz_service.quiz_repository.apply_scheduled_publishes",
        lambda conn: 0,
    )


# ----------------------------------------------------------------------
# TC-US01-01 — normal case
# ----------------------------------------------------------------------

def test_tc_us01_01_create_quiz_success(monkeypatch):
    """
    TC-US01-01 · US01 · normal

    A lecturer creates a quiz with a valid title, a 30-minute time limit,
    and a future due date. The service must return a QuizDetail with
    status="Draft" (US05: quizzes start as Draft) and no questions yet.
    """
    _patch_db(monkeypatch)

    payload = QuizCreateRequest(**mock_data_us01.VALID_PAYLOAD_KWARGS)
    result = create_quiz("lanpt@univ.edu", payload)

    assert result.quiz_id == 42
    assert result.title == "Midterm Quiz"
    assert result.time_limit_min == 30
    assert result.status == "Draft"
    assert result.questions == []


# ----------------------------------------------------------------------
# TC-US01-02 — error case
# ----------------------------------------------------------------------

def test_tc_us01_02_create_quiz_rejects_empty_title(monkeypatch):
    """
    TC-US01-02 · US01 · error

    A whitespace-only title must be rejected BEFORE any DB write — the
    validation runs first, so `insert_quiz` is never called.
    """
    _patch_db(monkeypatch)

    payload = QuizCreateRequest(
        course_id=1,
        title="   ",   # whitespace only — _validate_title strips and rejects
        time_limit_min=30,
        due_at=mock_data_us01.FUTURE_DUE_AT,
        publish_at=None,
    )

    with pytest.raises(ValidationError) as exc_info:
        create_quiz("lanpt@univ.edu", payload)

    assert "Title is required" in exc_info.value.message
    assert exc_info.value.status_code == 422


# ----------------------------------------------------------------------
# TC-US01-03 — boundary case on both sides of the BR2 limit
# ----------------------------------------------------------------------

@pytest.mark.parametrize(
    "time_limit, should_succeed",
    [
        pytest.param(4,   False, id="TC-US01-03a-below-min"),
        pytest.param(5,   True,  id="TC-US01-03b-at-min"),
        pytest.param(120, True,  id="TC-US01-03c-at-max"),
        pytest.param(121, False, id="TC-US01-03d-above-max"),
    ],
)
def test_tc_us01_03_create_quiz_time_limit_boundaries(
    monkeypatch, time_limit, should_succeed
):
    """
    TC-US01-03 · US01 · boundary

    BR2 says `time_limit_min` must be between 5 and 120 inclusive.
    This parametrized test checks both sides of both bounds:

        4    → rejected (below minimum)
        5    → accepted (on the minimum)
        120  → accepted (on the maximum)
        121  → rejected (above maximum)
    """
    _patch_db(monkeypatch, time_limit_min=time_limit)

    payload = QuizCreateRequest(
        course_id=1,
        title="Boundary Test Quiz",
        time_limit_min=time_limit,
        due_at=mock_data_us01.FUTURE_DUE_AT,
        publish_at=None,
    )

    if should_succeed:
        result = create_quiz("lanpt@univ.edu", payload)
        assert result.time_limit_min == time_limit
    else:
        with pytest.raises(ValidationError) as exc_info:
            create_quiz("lanpt@univ.edu", payload)
        assert "between 5 and 120" in exc_info.value.message
        assert exc_info.value.status_code == 422