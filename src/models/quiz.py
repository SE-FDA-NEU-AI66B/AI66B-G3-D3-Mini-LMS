"""
quiz.py — response shapes for quiz endpoints.

These Pydantic models are the API's public contract. They are deliberately
separate from the database rows: a repository may select more columns than
the API exposes, and the model is what the marker reads to understand the
response.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


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