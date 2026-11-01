"""
Mock data for US01 (Lecturer creates a quiz) test cases.

Everything here is a fixed, hardcoded constant — not generated, not read
from a file, not derived from the current date. That way the tests are
deterministic: they pass on any machine, on any day, forever.

The tuple layouts match the ones produced by the real SQL queries in
`src/repositories/instructor_quiz_repository.py`.
"""

from __future__ import annotations

from datetime import datetime


# A far-future date used as `due_at` on every valid quiz payload.
# Choosing 2099 makes the tests independent of "today's date".
FUTURE_DUE_AT = datetime(2099, 12, 31, 23, 59, 0)


# A valid lecturer row — matches `get_user_by_email` tuple layout:
#   (user_id, role, status)
LECTURER_ROW = (2, "Lecturer", "Active")


# A course row owned by the seeded lecturer (user_id 2) — matches
# `get_course` tuple layout:
#   (course_id, code, name, lecturer_id)
COURSE_OWNED_ROW = (1, "ACC101", "Introduction to Accounting", 2)


def quiz_row(
    quiz_id: int = 42,
    title: str = "Midterm Quiz",
    time_limit_min: int = 30,
) -> tuple:
    """
    A quiz row exactly as `repo.get_quiz` would return it, matching the
    `_QUIZ_SELECT` query layout (12 columns):

        quiz_id, course_id, code, created_by, title, time_limit_min,
        due_at, status, answers_released, created_at, lecturer_id,
        publish_at
    """
    return (
        quiz_id,          # quiz_id
        1,                # course_id
        "ACC101",         # course code
        2,                # created_by (lecturer user_id)
        title,            # title
        time_limit_min,   # time_limit_min
        FUTURE_DUE_AT,    # due_at
        "Draft",          # status — new quizzes start as Draft (US05)
        False,            # answers_released
        datetime(2025, 1, 1, 0, 0, 0),  # created_at (fixed)
        2,                # lecturer_id (owning lecturer)
        None,             # publish_at (no auto-publish scheduled)
    )


# A ready-made payload for the "happy path" test.
VALID_PAYLOAD_KWARGS = {
    "course_id": 1,
    "title": "Midterm Quiz",
    "time_limit_min": 30,
    "due_at": FUTURE_DUE_AT,
    "publish_at": None,
}