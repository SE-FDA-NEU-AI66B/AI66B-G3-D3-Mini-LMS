"""
attempt.py — request/response shapes for the student attempt flow (US03).

Deliberately separate from quiz.py so the "during attempt" contract
cannot accidentally leak `is_correct` or `accepted_answers`.

Every mutating operation (start / save / tab-switch / submit / heartbeat)
requires a `device_id` so the server can enforce "one device at a time".
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class AttemptQuestionOption(BaseModel):
    option_id: int
    label: str
    text: str


class AttemptQuestion(BaseModel):
    """A question as exposed DURING an attempt (no answers, no is_correct)."""
    question_id: int
    position: int
    question_type: Literal["MCQ", "SHORT"]
    prompt: str
    points: int
    options: list[AttemptQuestionOption] = Field(default_factory=list)


class SavedAnswer(BaseModel):
    question_id: int
    chosen_option_id: int | None = None
    text_answer: str | None = None


class AttemptState(BaseModel):
    attempt_id: int
    quiz_id: int
    quiz_title: str
    course_code: str
    time_limit_min: int
    started_at: datetime
    submitted_at: datetime | None = None
    remaining_seconds: int
    tab_switch_count: int
    flagged: bool
    questions: list[AttemptQuestion]
    saved_answers: list[SavedAnswer]


# ---- mutating requests — all require device_id -----------------------

class StartAttemptRequest(BaseModel):
    device_id: str = Field(..., min_length=1, max_length=128)
    takeover: bool = False


class SaveAnswerRequest(BaseModel):
    device_id: str = Field(..., min_length=1, max_length=128)
    chosen_option_id: int | None = None
    text_answer: str | None = None


class TabSwitchRequest(BaseModel):
    device_id: str = Field(..., min_length=1, max_length=128)


class TabSwitchResponse(BaseModel):
    tab_switch_count: int
    flagged: bool


class SubmitRequest(BaseModel):
    device_id: str = Field(..., min_length=1, max_length=128)
    auto_submitted: bool = False


class SubmitResponse(BaseModel):
    attempt_id: int
    score: int
    total: int
    percentage: float
    auto_submitted: bool


class HeartbeatRequest(BaseModel):
    device_id: str = Field(..., min_length=1, max_length=128)


class HeartbeatResponse(BaseModel):
    ok: bool
    remaining_seconds: int


class AttemptResult(BaseModel):
    attempt_id: int
    quiz_id: int
    quiz_title: str
    course_code: str
    score: int
    total: int
    percentage: float
    auto_submitted: bool
    submitted_at: datetime
    answers_released: bool