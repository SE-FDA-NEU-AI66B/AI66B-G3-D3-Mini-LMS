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

from src.models.quiz import QuizListResponse, StudentCourseListResponse
from src.services import quiz_service
from src.services.quiz_service import StudentNotFoundError

router = APIRouter(prefix="/api", tags=["quizzes"])


@router.get(
    "/quizzes",
    response_model=QuizListResponse,
    summary="List all quizzes visible to a student",
    description=(
        "Returns every Published quiz for a student who is actively "
        "enrolled in the owning course. Includes both 'available' "
        "and 'overdue' quizzes."
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


@router.get(
    "/student/courses",
    response_model=StudentCourseListResponse,
    summary="List courses a student is enrolled in",
    description="Returns the list of active courses for the student.",
)
def list_student_courses(
    email: str = Query(
        "minhhd@univ.edu",
        description="Student email.",
        examples=["minhhd@univ.edu"],
    ),
) -> StudentCourseListResponse:
    try:
        courses = quiz_service.list_student_courses(email)
    except StudentNotFoundError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    return StudentCourseListResponse(
        student_email=email,
        count=len(courses),
        courses=courses,
    )


@router.get(
    "/student/courses/{course_id}/quizzes",
    response_model=QuizListResponse,
    summary="List quizzes for a specific course",
    description="Returns the quizzes inside a specific course for the student.",
)
def list_course_quizzes(
    course_id: int,
    email: str = Query(
        "minhhd@univ.edu",
        description="Student email.",
        examples=["minhhd@univ.edu"],
    ),
) -> QuizListResponse:
    try:
        quizzes = quiz_service.list_course_quizzes(email, course_id)
    except StudentNotFoundError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    return QuizListResponse(
        student_email=email,
        count=len(quizzes),
        quizzes=quizzes,
    )