"""
Validation tests for the instructor quiz service (US01).

These tests never touch the database — they exercise the rules that run
before any connection is opened, so they are fast and deterministic.
"""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from src.models.quiz import (
    OptionInput,
    QuestionCreateRequest,
    QuizCreateRequest,
)
from src.services import instructor_quiz_service as svc
from src.services.instructor_quiz_service import ValidationError


FUTURE = datetime.utcnow() + timedelta(days=7)


# ------------------------------ quiz metadata -------------------------

def test_create_quiz_rejects_empty_title():
    with pytest.raises(ValidationError, match="Title is required"):
        svc.create_quiz(
            "lanpt@univ.edu",
            QuizCreateRequest(course_id=1, title="   ", time_limit_min=30, due_at=FUTURE),
        )


def test_create_quiz_rejects_time_limit_below_range():
    with pytest.raises(ValidationError, match="between 5 and 120"):
        svc.create_quiz(
            "lanpt@univ.edu",
            QuizCreateRequest(course_id=1, title="Midterm", time_limit_min=4, due_at=FUTURE),
        )


def test_create_quiz_rejects_time_limit_above_range():
    with pytest.raises(ValidationError, match="between 5 and 120"):
        svc.create_quiz(
            "lanpt@univ.edu",
            QuizCreateRequest(course_id=1, title="Midterm", time_limit_min=121, due_at=FUTURE),
        )


def test_create_quiz_accepts_boundary_time_limits():
    # 5 and 120 are the inclusive bounds of BR2. Reaching the DB is out
    # of scope here — we only assert that validation does NOT reject them.
    for minutes in (5, 120):
        try:
            svc.create_quiz(
                "lanpt@univ.edu",
                QuizCreateRequest(course_id=1, title="OK", time_limit_min=minutes, due_at=FUTURE),
            )
        except ValidationError:
            pytest.fail(f"{minutes} minutes should pass BR2 validation")


def test_create_quiz_rejects_past_due_date():
    with pytest.raises(ValidationError, match="future"):
        svc.create_quiz(
            "lanpt@univ.edu",
            QuizCreateRequest(
                course_id=1,
                title="Late",
                time_limit_min=30,
                due_at=datetime.utcnow() - timedelta(hours=1),
            ),
        )


# ------------------------------ question content ----------------------

def test_mcq_requires_exactly_four_options():
    with pytest.raises(ValidationError, match="exactly 4 options"):
        svc.create_question(
            "lanpt@univ.edu",
            1,
            QuestionCreateRequest(
                question_type="MCQ",
                prompt="2+2?",
                options=[
                    OptionInput(label="A", text="3"),
                    OptionInput(label="B", text="4", is_correct=True),
                    OptionInput(label="C", text="5"),
                ],
            ),
        )


def test_mcq_requires_exactly_one_correct_option():
    with pytest.raises(ValidationError, match="exactly 1 correct"):
        svc.create_question(
            "lanpt@univ.edu",
            1,
            QuestionCreateRequest(
                question_type="MCQ",
                prompt="2+2?",
                options=[
                    OptionInput(label="A", text="3", is_correct=True),
                    OptionInput(label="B", text="4", is_correct=True),
                    OptionInput(label="C", text="5"),
                    OptionInput(label="D", text="6"),
                ],
            ),
        )


def test_short_requires_accepted_answer():
    with pytest.raises(ValidationError, match="accepted answer"):
        svc.create_question(
            "lanpt@univ.edu",
            1,
            QuestionCreateRequest(
                question_type="SHORT", prompt="Capital of Vietnam?",
                accepted_answers=[],
            ),
        )


def test_short_requires_non_blank_accepted_answer():
    with pytest.raises(ValidationError, match="non-empty"):
        svc.create_question(
            "lanpt@univ.edu",
            1,
            QuestionCreateRequest(
                question_type="SHORT", prompt="Capital?",
                accepted_answers=["   ", ""],
            ),
        )


# ------------------------------ normalisation -------------------------

def test_parse_accepted_answers_handles_json_and_plain_text():
    assert svc._parse_accepted_answers('["Hà Nội","Ha Noi"]') == ["Hà Nội", "Ha Noi"]
    # Seeded data stores a plain string, not JSON.
    assert svc._parse_accepted_answers("sample accepted answer") == ["sample accepted answer"]
    assert svc._parse_accepted_answers(None) == []