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

from src.models.quiz import QuizListItem, StudentCourseSummary
from src.repositories import quiz_repository


class StudentNotFoundError(Exception):
    """Raised when the caller asks for a student the system does not know,
    or when the caller is authenticated but not permitted."""


def _verify_student_role(student_email: str) -> None:
    """
    Role gate (defence-in-depth):
      - the account must exist,
      - it must be Active,
      - it must have role = Student.
    
    Raises StudentNotFoundError if any check fails.
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


def list_visible_quizzes(student_email: str) -> list[QuizListItem]:
    """
    Return all quizzes visible to `student_email` (both available and overdue).
    
    BR6 is enforced downstream in the query:
      - the quiz must be Published,
      - the student must be enrolled with status = Active.
    """
    _verify_student_role(student_email)
    return quiz_repository.find_visible_quizzes(student_email)


def list_course_quizzes(student_email: str, course_id: int) -> list[QuizListItem]:
    """
    Return the quizzes inside a specific course for the given student.
    """
    _verify_student_role(student_email)
    return quiz_repository.find_course_quizzes(student_email, course_id)


def list_student_courses(student_email: str) -> list[StudentCourseSummary]:
    """
    Return the list of courses the student is actively enrolled in.
    """
    _verify_student_role(student_email)
    courses_data = quiz_repository.find_student_courses(student_email)
    
    # Map the repository dictionaries to the Pydantic model
    return [StudentCourseSummary(**c) for c in courses_data]