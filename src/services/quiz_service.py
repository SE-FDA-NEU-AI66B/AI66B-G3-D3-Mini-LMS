"""
quiz_service.py — business logic for quiz listings.

The service does not know about HTTP. It does not know about SQL. It
receives a plain argument and returns a plain result. That is what makes
the rules unit-testable without a server and without a database.

This service now enforces a role gate: only an Active *Student* may reach
the student quiz list. A Lecturer or Admin who used to be a Student (and
still has enrollment rows) is rejected — their data stays intact for a
future demotion, but they cannot access the student endpoint.
"""

from __future__ import annotations

from src.models.quiz import QuizListItem
from src.repositories import quiz_repository


class StudentNotFoundError(Exception):
    """Raised when the caller asks for a student the system does not know,
    or when the caller is authenticated but not permitted."""


def list_visible_quizzes(student_email: str) -> list[QuizListItem]:
    """
    Return the quizzes visible to `student_email`.

    BR6 is enforced downstream in the query:
      - the quiz must be Published,
      - the due date must be in the future,
      - the student must be enrolled with status = Active.

    Role gate (defence-in-depth):
      - the account must exist,
      - it must be Active,
      - it must have role = Student.
    """
    if not student_email or "@" not in student_email:
        raise StudentNotFoundError(f"Invalid student email: {student_email!r}")

    row = quiz_repository.get_user_role_status(student_email)
    if row is None:
        raise StudentNotFoundError(f"Unknown account: {student_email!r}")
    _user_id, role, status = row
    if status != "Active":
        raise StudentNotFoundError(f"Account is disabled: {student_email!r}")
    if role != "Student":
        raise StudentNotFoundError(
            f"{student_email} is not a student (role: {role})"
        )

    return quiz_repository.find_visible_quizzes(student_email)