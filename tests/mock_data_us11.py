"""
Mock data for US11 (Admin creates a course and assigns a lecturer).

All values are hardcoded constants — nothing derived from the current
date or from a real database. The tests stay deterministic on any
machine, on any day.

Tuple layouts match the ones produced by `get_user` and
`get_course_admin` in `src/repositories/admin_repository.py`.
"""

from __future__ import annotations

from datetime import datetime


FIXED_CREATED_AT = datetime(2025, 1, 1, 0, 0, 0)


# get_user_role_status layout: (user_id, role, status).
# The seeded Admin (user_id 1) — caller of every service function.
ADMIN_AUTH_ROW = (1, "Admin", "Active")


# get_user layout: (user_id, email, full_name, role, status, created_at).

def user_row(
    user_id: int,
    email: str,
    full_name: str,
    role: str,
    status: str = "Active",
) -> tuple:
    return (user_id, email, full_name, role, status, FIXED_CREATED_AT)


# A valid Lecturer — used by every success path.
VALID_LECTURER_ROW = user_row(
    user_id=2,
    email="lanpt@univ.edu",
    full_name="Pham Thi Lan",
    role="Lecturer",
)


# An existing user who is NOT a Lecturer — used by the wrong-role boundary.
NON_LECTURER_ROW = user_row(
    user_id=1,
    email="admin@univ.edu",
    full_name="Nguyen Thi Mai",
    role="Admin",
)


# get_course_admin layout:
#   (course_id, code, name, lecturer_id, lecturer_name,
#    lecturer_email, student_count)

def course_row(
    course_id: int,
    code: str,
    name: str,
    lecturer_id: int,
    lecturer_name: str = "Pham Thi Lan",
    lecturer_email: str = "lanpt@univ.edu",
    student_count: int = 0,
) -> tuple:
    return (
        course_id, code, name,
        lecturer_id, lecturer_name, lecturer_email, student_count,
    )


# A pre-existing course — returned by `get_course_by_code` in the
# duplicate-code test. Layout: (course_id,).
EXISTING_COURSE_CODE_ROW = (3,)