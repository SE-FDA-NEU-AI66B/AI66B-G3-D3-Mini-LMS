"""
quiz.py — response shapes for quiz endpoints.

These Pydantic models are the API's public contract. They are deliberately
separate from the database rows: a repository may select more columns than
the API exposes, and the model is what the marker reads to understand the
response.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

# ----------------------------------------------------------------------
# Student — walking skeleton
# ----------------------------------------------------------------------

class QuizListItem(BaseModel):
    """One row in GET /api/quizzes — the walking-skeleton response."""

    quiz_id: int = Field(..., description="Primary key of the quiz")
    title: str = Field(..., description="Quiz title")
    course_code: str = Field(..., description="Course code, e.g. ACC101")
    due_at: datetime = Field(..., description="Submission deadline (UTC)")
    time_limit_min: int = Field(..., description="Time limit in minutes (5–120)")


class QuizListResponse(BaseModel):
    """Envelope returned by GET /api/quizzes."""

    student_email: str
    count: int
    quizzes: list[QuizListItem]


# ----------------------------------------------------------------------
# Instructor — quiz CRUD (US01)
# ----------------------------------------------------------------------

class QuizCreateRequest(BaseModel):
    course_id: int = Field(..., gt=0)
    title: str = Field(..., description="Quiz title (required)")
    time_limit_min: int = Field(..., description="5–120 minutes (BR2)")
    due_at: datetime = Field(..., description="Deadline; must be in the future")


class QuizUpdateRequest(BaseModel):
    title: str
    time_limit_min: int
    due_at: datetime


class QuizSummary(BaseModel):
    """One row in GET /api/instructor/quizzes."""

    quiz_id: int
    course_id: int
    course_code: str
    title: str
    time_limit_min: int
    due_at: datetime
    status: str
    question_count: int
    created_at: datetime


class InstructorQuizListResponse(BaseModel):
    lecturer_email: str
    count: int
    quizzes: list[QuizSummary]


class OptionInput(BaseModel):
    label: str = Field(..., min_length=1, max_length=1,
                       description="Single character: A, B, C, D")
    text: str = Field(..., min_length=1)
    is_correct: bool = False


class OptionResponse(BaseModel):
    option_id: int
    label: str
    text: str
    is_correct: bool


class QuestionCreateRequest(BaseModel):
    question_type: Literal["MCQ", "SHORT"]
    prompt: str
    position: int | None = Field(
        default=None,
        description="Optional. If omitted, the next free position is used.",
    )
    options: list[OptionInput] | None = Field(
        default=None,
        description="Required for MCQ: exactly 4 options, exactly 1 correct.",
    )
    accepted_answers: list[str] | None = Field(
        default=None,
        description="Required for SHORT: at least one accepted answer.",
    )


class QuestionUpdateRequest(BaseModel):
    question_type: Literal["MCQ", "SHORT"]
    prompt: str
    options: list[OptionInput] | None = None
    accepted_answers: list[str] | None = None


class QuestionResponse(BaseModel):
    question_id: int
    quiz_id: int
    position: int
    question_type: str
    prompt: str
    points: int
    options: list[OptionResponse]
    accepted_answers: list[str]


class QuizDetail(BaseModel):
    """Full quiz, including its questions. Returned by create / get / update."""

    quiz_id: int
    course_id: int
    course_code: str
    created_by: int
    title: str
    time_limit_min: int
    due_at: datetime
    status: str
    answers_released: bool
    created_at: datetime
    questions: list[QuestionResponse]


class QuizDeleteResponse(BaseModel):
    deleted: bool
    quiz_id: int


class QuestionDeleteResponse(BaseModel):
    deleted: bool
    question_id: int

# ----------------------------------------------------------------------
# Instructor — course list (supporting US01)
# ----------------------------------------------------------------------

class CourseSummary(BaseModel):
    course_id: int
    code: str
    name: str


class InstructorCourseListResponse(BaseModel):
    lecturer_email: str
    count: int
    courses: list[CourseSummary]