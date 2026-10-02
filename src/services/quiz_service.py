"""
quiz_service.py — business logic for quiz listings.

The service does not know about HTTP. It does not know about SQL. It
receives a plain argument and returns a plain result. That is what makes
the rules unit-testable without a server and without a database.
"""

from __future__ import annotations

from src.models.quiz import QuizListItem
from src.repositories import quiz_repository


class StudentNotFoundError(Exception):
    """Raised when the caller asks for a student the system does not know."""


def list_visible_quizzes(student_email: str) -> list[QuizListItem]:
    """
    Return the quizzes visible to `student_email`.

    BR6 is enforced here:
      - the quiz must be Published,
      - the due date must be in the future,
      - the student must be enrolled with status = Active.

    The current implementation pushes all three filters into the query
    for efficiency. When BR6 gains a fourth condition, this function is
    the single place to change.
    """
    if not student_email or "@" not in student_email:
        raise StudentNotFoundError(f"Invalid student email: {student_email!r}")

    return quiz_repository.find_visible_quizzes(student_email)