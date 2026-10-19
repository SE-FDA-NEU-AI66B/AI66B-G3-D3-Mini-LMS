"""
attempt_routes.py — HTTP layer for the student attempt flow (US03).

Every mutating route requires a `device_id` so the service can enforce
"one device at a time". Read-only routes stay auth-only.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from src.models.attempt import (
    AttemptResult,
    AttemptState,
    HeartbeatRequest,
    HeartbeatResponse,
    SaveAnswerRequest,
    StartAttemptRequest,
    SubmitRequest,
    SubmitResponse,
    TabSwitchRequest,
    TabSwitchResponse,
)
from src.routes.deps import current_email
from src.services import attempt_service

router = APIRouter(prefix="/api", tags=["attempts"])


# ----------------------------- start / resume -------------------------

@router.post(
    "/quizzes/{quiz_id}/attempts",
    response_model=AttemptState,
    summary="Start or resume an attempt (US03, BR1, device lease)",
)
def start_attempt(
    quiz_id: int,
    payload: StartAttemptRequest,
    email: str = Depends(current_email),
) -> AttemptState:
    return attempt_service.start_attempt(
        email, quiz_id, payload.device_id, payload.takeover,
    )


@router.get(
    "/attempts/{attempt_id}",
    response_model=AttemptState,
    summary="Read the state of an in-progress attempt (no lease required)",
)
def get_attempt(
    attempt_id: int, email: str = Depends(current_email)
) -> AttemptState:
    return attempt_service.get_attempt(email, attempt_id)


# ------------------------------- answering ----------------------------

@router.put(
    "/attempts/{attempt_id}/answers/{question_id}",
    summary="Save one answer (requires device lease)",
)
def save_answer(
    attempt_id: int,
    question_id: int,
    payload: SaveAnswerRequest,
    email: str = Depends(current_email),
):
    return attempt_service.save_answer(email, attempt_id, question_id, payload)


# ----------------------------- tab-switch -----------------------------

@router.post(
    "/attempts/{attempt_id}/tab-switch",
    response_model=TabSwitchResponse,
    summary="Record a tab-switch (BR10, requires device lease)",
)
def record_tab_switch(
    attempt_id: int,
    payload: TabSwitchRequest,
    email: str = Depends(current_email),
) -> TabSwitchResponse:
    return attempt_service.record_tab_switch(email, attempt_id, payload.device_id)


# ----------------------------- submit / result ------------------------

@router.post(
    "/attempts/{attempt_id}/submit",
    response_model=SubmitResponse,
    summary="Submit and grade (requires device lease)",
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


# ------------------------- heartbeat / release ------------------------

@router.post(
    "/attempts/{attempt_id}/heartbeat",
    response_model=HeartbeatResponse,
    summary="Refresh the device lease (called every ~10 s by the client)",
)
def heartbeat(
    attempt_id: int,
    payload: HeartbeatRequest,
    email: str = Depends(current_email),
) -> HeartbeatResponse:
    data = attempt_service.heartbeat(email, attempt_id, payload.device_id)
    return HeartbeatResponse(**data)


@router.post(
    "/attempts/{attempt_id}/release",
    summary="Release the device lease (called on beforeunload via sendBeacon)",
)
def release(
    attempt_id: int,
    device_id: str = Query(..., min_length=1, max_length=128),
    email: str = Depends(current_email),
):
    attempt_service.release_lease(email, attempt_id, device_id)
    return {"ok": True}