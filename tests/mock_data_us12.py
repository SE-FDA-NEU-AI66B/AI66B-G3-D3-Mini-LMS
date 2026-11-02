"""
Mock data for US12 (Admin enrolls students into a course).

All values are hardcoded constants — nothing derived from the current
date or from a real database. The tests stay deterministic on any
machine, on any day.

Tuple layouts match the ones produced by the real SQL queries in
`src/repositories/admin_repository.py`.
"""

from __future__ import annotations

from datetime import datetime


FIXED_CREATED_AT = datetime(2025, 1, 1, 0, 0, 0)
COURSE_ID = 1


# get_user_role_status layout: (user_id, role, status).
# The seeded Admin (user_id 1) — caller of every service function.
ADMIN_AUTH_ROW = (1, "Admin", "Active")


# get_course_admin layout:
#   (course_id, code, name, lecturer_id, lecturer_name,
#    lecturer_email, student_count)
COURSE_ROW = (
    COURSE_ID,
    "ACC101",
    "Introduction to Accounting",
    2,
    "Pham Thi Lan",
    "lanpt@univ.edu",
    10,
)


# get_user_by_email layout: (user_id, role, status).

# A valid Active Student — used by every success path.
ACTIVE_STUDENT_ROW = (4, "Student", "Active")

# A Disabled Student — account-status boundary test.
DISABLED_STUDENT_ROW = (5, "Student", "Disabled")

# A Lecturer — wrong-role boundary test.
LECTURER_ROW = (2, "Lecturer", "Active")


# get_enrollment_status returns a bare string or None.
# The three possible values are used by the boundary test:
#   None      → no enrollment exists  (new enrollment)
#   "Active"  → student is enrolled   (409 conflict)
#   "Removed" → was enrolled, removed (re-enrollment restores)
ENROLLMENT_NONE    = None
ENROLLMENT_ACTIVE  = "Active"
ENROLLMENT_REMOVED = "Removed"