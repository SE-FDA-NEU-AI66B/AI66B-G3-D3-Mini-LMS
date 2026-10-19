"""
attempt_routes.py — HTTP layer for the student attempt flow (US03).

Thin: parse, call service, return. All errors bubble as
`AttemptServiceError` subclasses and are translated in app.py.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from src.models.attempt import (
    AttemptResult,
    AttemptState,
    SaveAnswerRequest,
    SubmitRequest,
    SubmitResponse,
    TabSwitchResponse,
)
from src.routes.deps import current_email
from src.services import attempt_service

router = APIRouter(prefix="/api", tags=["attempts"])


@router.post(
    "/quizzes/{quiz_id}/attempts",
    response_model=AttemptState,
    summary="Start or resume a quiz attempt (US03, BR1)",
)
def start_attempt(
    quiz_id: int, email: str = Depends(current_email)
) -> AttemptState:
    return attempt_service.start_attempt(email, quiz_id)


@router.get(
    "/attempts/{attempt_id}",
    response_model=AttemptState,
    summary="Get the state of an in-progress attempt",
)
def get_attempt(
    attempt_id: int, email: str = Depends(current_email)
) -> AttemptState:
    return attempt_service.get_attempt(email, attempt_id)


@router.put(
    "/attempts/{attempt_id}/answers/{question_id}",
    summary="Save one answer for a question (US03)",
)
def save_answer(
    attempt_id: int,
    question_id: int,
    payload: SaveAnswerRequest,
    email: str = Depends(current_email),
):
    return attempt_service.save_answer(email, attempt_id, question_id, payload)


@router.post(
    "/attempts/{attempt_id}/tab-switch",
    response_model=TabSwitchResponse,
    summary="Record a tab-switch event (BR10)",
)
def record_tab_switch(
    attempt_id: int, email: str = Depends(current_email)
) -> TabSwitchResponse:
    return attempt_service.record_tab_switch(email, attempt_id)


@router.post(
    "/attempts/{attempt_id}/submit",
    response_model=SubmitResponse,
    summary="Submit an attempt and grade it (US03, US04)",
)
def submit_attempt(
    attempt_id: int,
    payload: SubmitRequest,
    email: str = Depends(current_email),
) -> SubmitResponse:
    return attempt_service.submit_attempt(email, attempt_id, payload)


@router.get(
    "/attempts/{attempt_id}/result",
    response_model=AttemptResult,
    summary="Get the result of a submitted attempt",
)
def get_result(
    attempt_id: int, email: str = Depends(current_email)
) -> AttemptResult:
    return attempt_service.get_result(email, attempt_id)