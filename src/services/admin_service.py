"""
admin_service.py — business logic for admin user & course management.
"""

from __future__ import annotations

from src.config import db as db_config
from src.models.admin import (
    AdminCourseListResponse,
    AdminCourseResponse,
    CourseRosterEntry,
    CourseRosterResponse,
    UserAdminListResponse,
    UserAdminResponse,
    UserCreateRequest,
    UserUpdateRequest,
    CourseCreateRequest,
    CourseUpdateRequest,
)
from src.repositories import admin_repository as repo
from src.utils.password import hash_password


# ----------------------------------------------------------------------
# Errors
# ----------------------------------------------------------------------

class AdminServiceError(Exception):
    def __init__(self, message: str, status_code: int = 400) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code


class UnauthorizedError(AdminServiceError):
    def __init__(self, message: str = "Not authenticated") -> None:
        super().__init__(message, 401)


class ForbiddenError(AdminServiceError):
    def __init__(self, message: str = "Access denied") -> None:
        super().__init__(message, 403)


class NotFoundError(AdminServiceError):
    def __init__(self, message: str = "Not found") -> None:
        super().__init__(message, 404)


class ConflictError(AdminServiceError):
    def __init__(self, message: str = "Conflict") -> None:
        super().__init__(message, 409)


class ValidationError(AdminServiceError):
    def __init__(self, message: str = "Invalid input") -> None:
        super().__init__(message, 422)


# ----------------------------------------------------------------------
# Auth & Helpers
# ----------------------------------------------------------------------

def _require_admin(conn, email: str) -> int:
    if not email or "@" not in email:
        raise UnauthorizedError()
    row = repo.get_user_role_status(conn, email)
    if row is None:
        raise UnauthorizedError(f"Unknown account: {email!r}")
    user_id, role, status = row
    if status != "Active":
        raise ForbiddenError("Account is disabled")
    if role != "Admin":
        raise ForbiddenError("Only admins may manage accounts and courses")
    return user_id


def _row_to_user(row: tuple) -> UserAdminResponse:
    return UserAdminResponse(
        user_id=row[0], email=row[1], full_name=row[2],
        role=row[3], status=row[4], created_at=row[5],
    )


def _row_to_course(row: tuple) -> AdminCourseResponse:
    return AdminCourseResponse(
        course_id=row[0], code=row[1], name=row[2],
        lecturer_id=row[3], lecturer_name=row[4],
        lecturer_email=row[5], student_count=row[6],
    )


# ----------------------------------------------------------------------
# User CRUD
# ----------------------------------------------------------------------

def list_users(admin_email: str, role: str | None = None, status: str | None = None, q: str | None = None, user_id: int | None = None) -> UserAdminListResponse:
    with db_config.connect() as conn:
        _require_admin(conn, admin_email)
        rows = repo.list_users(conn, role=role, status=status, q=q, user_id=user_id)
    users = [_row_to_user(r) for r in rows]
    return UserAdminListResponse(count=len(users), users=users)


def get_user(admin_email: str, user_id: int) -> UserAdminResponse:
    with db_config.connect() as conn:
        _require_admin(conn, admin_email)
        row = repo.get_user(conn, user_id)
    if row is None:
        raise NotFoundError(f"User {user_id} not found")
    return _row_to_user(row)


def create_user(admin_email: str, payload: UserCreateRequest) -> UserAdminResponse:
    email = (payload.email or "").strip().lower()
    full_name = (payload.full_name or "").strip()
    if not email or "@" not in email:
        raise ValidationError("A valid email is required")
    if not full_name:
        raise ValidationError("Full name is required")
    if not payload.password:
        raise ValidationError("Initial password is required")

    with db_config.connect() as conn:
        _require_admin(conn, admin_email)
        if repo.get_user_by_email_admin(conn, email) is not None:
            raise ConflictError(f"Email {email!r} is already in use")
        pw_hash = hash_password(payload.password)
        user_id = repo.insert_user(conn, email, full_name, pw_hash, payload.role, payload.status)
        row = repo.get_user(conn, user_id)
        return _row_to_user(row)


def update_user(admin_email: str, user_id: int, payload: UserUpdateRequest) -> UserAdminResponse:
    with db_config.connect() as conn:
        admin_id = _require_admin(conn, admin_email)
        current = repo.get_user(conn, user_id)
        if current is None:
            raise NotFoundError(f"User {user_id} not found")

        new_email = (payload.email or current[1]).strip().lower()
        new_name = (payload.full_name or current[2]).strip()
        new_role = payload.role or current[3]
        new_status = payload.status or current[4]

        if not new_email or "@" not in new_email:
            raise ValidationError("A valid email is required")
        if not new_name:
            raise ValidationError("Full name is required")

        if user_id == admin_id and new_role != "Admin":
            raise ConflictError("You cannot change your own admin role")
        if user_id == admin_id and new_status != "Active":
            raise ConflictError("You cannot disable your own account")

        if current[3] == "Lecturer" and new_role != "Lecturer":
            deps = repo.count_user_dependencies(conn, user_id)
            if deps["courses"] > 0:
                raise ConflictError(
                    f"This lecturer still owns {deps['courses']} course(s). "
                    "Reassign those courses to another lecturer before changing the role (BR9)."
                )

        if new_email != current[1]:
            other = repo.get_user_by_email_admin(conn, new_email)
            if other is not None and other[0] != user_id:
                raise ConflictError(f"Email {new_email!r} is already in use")

        pw_hash = hash_password(payload.password) if payload.password else None
        repo.update_user(conn, user_id, new_email, new_name, new_role, new_status, pw_hash)
        row = repo.get_user(conn, user_id)
        return _row_to_user(row)


def delete_user(admin_email: str, user_id: int) -> None:
    with db_config.connect() as conn:
        admin_id = _require_admin(conn, admin_email)
        if user_id == admin_id:
            raise ConflictError("You cannot delete your own account")
        row = repo.get_user(conn, user_id)
        if row is None:
            raise NotFoundError(f"User {user_id} not found")

        deps = repo.count_user_dependencies(conn, user_id)
        blocking = {k: v for k, v in deps.items() if v > 0}
        if blocking:
            detail = ", ".join(f"{k}={v}" for k, v in blocking.items())
            raise ConflictError(
                f"Cannot delete user: still referenced by {detail}. "
                "Disable the account instead."
            )
        repo.delete_user(conn, user_id)


# ----------------------------------------------------------------------
# Course CRUD (US11)
# ----------------------------------------------------------------------

def list_courses(admin_email: str) -> AdminCourseListResponse:
    with db_config.connect() as conn:
        _require_admin(conn, admin_email)
        rows = repo.list_courses_admin(conn)
    courses = [_row_to_course(r) for r in rows]
    return AdminCourseListResponse(count=len(courses), courses=courses)


def create_course(admin_email: str, payload: CourseCreateRequest) -> AdminCourseResponse:
    code = payload.code.strip().upper()
    name = payload.name.strip()

    if not code or not name:
        raise ValidationError("Course code and name are required")

    with db_config.connect() as conn:
        _require_admin(conn, admin_email)

        if repo.get_course_by_code(conn, code) is not None:
            raise ConflictError(f"Course code '{code}' already exists.")

        lecturer = repo.get_user(conn, payload.lecturer_id)
        if lecturer is None or lecturer[3] != "Lecturer":
            raise ValidationError("The assigned user must be a valid Lecturer.")

        course_id = repo.insert_course(conn, code, name, payload.lecturer_id)
        row = repo.get_course_admin(conn, course_id)
        return _row_to_course(row)


def update_course(admin_email: str, course_id: int, payload: CourseUpdateRequest) -> AdminCourseResponse:
    with db_config.connect() as conn:
        _require_admin(conn, admin_email)

        current = repo.get_course_admin(conn, course_id)
        if current is None:
            raise NotFoundError(f"Course {course_id} not found")

        new_code = payload.code.strip().upper() if payload.code else current[1]
        new_name = payload.name.strip() if payload.name else current[2]
        new_lecturer_id = payload.lecturer_id if payload.lecturer_id else current[3]

        if new_code != current[1]:
            existing = repo.get_course_by_code(conn, new_code)
            if existing is not None and existing[0] != course_id:
                raise ConflictError(f"Course code '{new_code}' already exists.")

        if new_lecturer_id != current[3]:
            lecturer = repo.get_user(conn, new_lecturer_id)
            if lecturer is None or lecturer[3] != "Lecturer":
                raise ValidationError("The assigned user must be a valid Lecturer.")

        repo.update_course(conn, course_id, new_code, new_name, new_lecturer_id)
        row = repo.get_course_admin(conn, course_id)
        return _row_to_course(row)


def delete_course(admin_email: str, course_id: int) -> None:
    with db_config.connect() as conn:
        _require_admin(conn, admin_email)

        current = repo.get_course_admin(conn, course_id)
        if current is None:
            raise NotFoundError(f"Course {course_id} not found")

        # HARD DELETE: Cascade delete all related students, quizzes, attempts, etc.
        repo.delete_course_cascade(conn, course_id)


# ----------------------------------------------------------------------
# Roster & Enrollments (US12)
# ----------------------------------------------------------------------

def get_course_roster(admin_email: str, course_id: int) -> CourseRosterResponse:
    with db_config.connect() as conn:
        _require_admin(conn, admin_email)
        course = repo.get_course_admin(conn, course_id)
        if course is None:
            raise NotFoundError(f"Course {course_id} not found")
        lecturer_row = repo.get_user(conn, course[3])
        enrollments = repo.list_course_enrollments(conn, course_id)

    lecturer = _row_to_user(lecturer_row) if lecturer_row else None
    students = [
        CourseRosterEntry(
            user_id=r[0], email=r[1], full_name=r[2],
            status=r[3], enrolled_at=r[4], role=r[5]
        )
        for r in enrollments
    ]
    return CourseRosterResponse(
        course_id=course[0], code=course[1], name=course[2],
        lecturer=lecturer, students=students,
    )


def add_enrollment(admin_email: str, course_id: int, student_email: str) -> None:
    with db_config.connect() as conn:
        _require_admin(conn, admin_email)
        course = repo.get_course_admin(conn, course_id)
        if course is None:
            raise NotFoundError(f"Course {course_id} not found")

        student_email = student_email.strip().lower()
        user_row = repo.get_user_by_email(conn, student_email)
        if not user_row:
            raise ValidationError(f"Account '{student_email}' not found.")

        user_id, role, status = user_row
        if role != "Student":
            raise ValidationError(f"'{student_email}' is a {role}, not a Student.")
        if status != "Active":
            raise ValidationError(f"'{student_email}' is disabled. Enable the account first.")

        existing_status = repo.get_enrollment_status(conn, course_id, user_id)
        if existing_status == "Active":
            raise ConflictError(f"Student '{student_email}' is already enrolled in this course.")

        repo.upsert_enrollment(conn, course_id, user_id, "Active")


def remove_enrollment(admin_email: str, course_id: int, student_id: int) -> None:
    with db_config.connect() as conn:
        _require_admin(conn, admin_email)
        course = repo.get_course_admin(conn, course_id)
        if course is None:
            raise NotFoundError(f"Course {course_id} not found")

        existing_status = repo.get_enrollment_status(conn, course_id, student_id)
        if existing_status is None:
            raise NotFoundError("Enrollment not found.")
        if existing_status == "Removed":
            raise ConflictError("Student is already removed from this course.")

        repo.upsert_enrollment(conn, course_id, student_id, "Removed")