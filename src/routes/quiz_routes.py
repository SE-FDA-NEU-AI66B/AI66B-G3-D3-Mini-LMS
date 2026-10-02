"""
quiz_routes.py — HTTP layer for quiz endpoints.

Responsibilities of this file:
  - Parse and validate the request.
  - Call the service.
  - Translate service results into HTTP responses.
  - Translate service exceptions into HTTP status codes.

It contains no SQL and no business rules.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from src.models.quiz import QuizListResponse
from src.services import quiz_service
from src.services.quiz_service import StudentNotFoundError


router = APIRouter(prefix="/api", tags=["quizzes"])


@router.get(
    "/quizzes",
    response_model=QuizListResponse,
    summary="List quizzes visible to a student",
    description=(
        "Walking-skeleton endpoint. Returns every Published quiz whose "
        "due date is in the future, for a student who is actively "
        "enrolled in the owning course. This is the SQL that powers the "
        "M2 walking skeleton."
    ),
)
def list_quizzes(
    email: str = Query(
        "minhhd@univ.edu",
        description="Student email. Defaults to the seeded student.",
        examples=["minhhd@univ.edu", "anhnv@univ.edu"],
    ),
) -> QuizListResponse:
    try:
        quizzes = quiz_service.list_visible_quizzes(email)
    except StudentNotFoundError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    return QuizListResponse(
        student_email=email,
        count=len(quizzes),
        quizzes=quizzes,
    )