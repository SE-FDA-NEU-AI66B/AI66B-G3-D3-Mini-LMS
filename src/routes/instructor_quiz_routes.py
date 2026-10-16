"""
instructor_quiz_routes.py — HTTP layer for lecturer quiz CRUD (US01).

Responsibilities of this file:
  - Parse and validate the request shape.
  - Call the service.
  - Return the service result.
  - Let `InstructorServiceError` be translated centrally in app.py.

It contains no SQL and no business rules.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, status

from src.models.quiz import (
    InstructorQuizListResponse,
    QuestionCreateRequest,
    QuestionDeleteResponse,
    QuestionResponse,
    QuestionUpdateRequest,
    QuizCreateRequest,
    QuizDeleteResponse,
    QuizDetail,
    QuizUpdateRequest,
)
from src.routes.deps import current_email
from src.services import instructor_quiz_service as service


router = APIRouter(prefix="/api/instructor", tags=["instructor-quizzes"])


# ------------------------------- quizzes ------------------------------

@router.get(
    "/quizzes",
    response_model=InstructorQuizListResponse,
    summary="List the calling lecturer's quizzes",
)
def list_quizzes(email: str = Depends(current_email)) -> InstructorQuizListResponse:
    quizzes = service.list_quizzes(email)
    return InstructorQuizListResponse(
        lecturer_email=email, count=len(quizzes), quizzes=quizzes
    )


@router.post(
    "/quizzes",
    response_model=QuizDetail,
    status_code=status.HTTP_201_CREATED,
    summary="Create a quiz inside one of the lecturer's courses (US01)",
)
def create_quiz(
    payload: QuizCreateRequest, email: str = Depends(current_email)
) -> QuizDetail:
    return service.create_quiz(email, payload)


@router.get(
    "/quizzes/{quiz_id}",
    response_model=QuizDetail,
    summary="Get one quiz with its questions",
)
def get_quiz(quiz_id: int, email: str = Depends(current_email)) -> QuizDetail:
    return service.get_quiz(email, quiz_id)


@router.put(
    "/quizzes/{quiz_id}",
    response_model=QuizDetail,
    summary="Update a quiz's title, time limit, or due date",
)
def update_quiz(
    quiz_id: int, payload: QuizUpdateRequest, email: str = Depends(current_email)
) -> QuizDetail:
    return service.update_quiz(email, quiz_id, payload)


@router.delete(
    "/quizzes/{quiz_id}",
    response_model=QuizDeleteResponse,
    summary="Delete a quiz (blocked if any attempt exists)",
)
def delete_quiz(
    quiz_id: int, email: str = Depends(current_email)
) -> QuizDeleteResponse:
    service.delete_quiz(email, quiz_id)
    return QuizDeleteResponse(deleted=True, quiz_id=quiz_id)


# ------------------------------ questions -----------------------------

@router.post(
    "/quizzes/{quiz_id}/questions",
    response_model=QuestionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add an MCQ or SHORT question to a quiz (US01)",
)
def create_question(
    quiz_id: int, payload: QuestionCreateRequest, email: str = Depends(current_email)
) -> QuestionResponse:
    return service.create_question(email, quiz_id, payload)


@router.put(
    "/quizzes/{quiz_id}/questions/{question_id}",
    response_model=QuestionResponse,
    summary="Replace a question's prompt, options, or accepted answers",
)
def update_question(
    quiz_id: int,
    question_id: int,
    payload: QuestionUpdateRequest,
    email: str = Depends(current_email),
) -> QuestionResponse:
    return service.update_question(email, quiz_id, question_id, payload)


@router.delete(
    "/quizzes/{quiz_id}/questions/{question_id}",
    response_model=QuestionDeleteResponse,
    summary="Delete a question from a quiz",
)
def delete_question(
    quiz_id: int, question_id: int, email: str = Depends(current_email)
) -> QuestionDeleteResponse:
    service.delete_question(email, quiz_id, question_id)
    return QuestionDeleteResponse(deleted=True, question_id=question_id)