"""
Mock data for US05 (Lecturer publishes / unpublishes a quiz).

All values are hardcoded constants — the "now" used by the service is
pinned to FIXED_NOW via monkeypatch, so the tests stay deterministic on
any machine, on any day.

Tuple layouts match the ones produced by `get_quiz` in
`src/repositories/instructor_quiz_repository.py`.
"""

from __future__ import annotations

from datetime import datetime, timedelta


# Fixed "now" — the service's `_now_utc_naive()` is monkeypatched to
# return exactly this value, so the due-date boundary test never depends
# on the current wall clock.
FIXED_NOW = datetime(2026, 1, 15, 12, 0, 0)


# Due-date values relative to FIXED_NOW — used by the boundary test.
DUE_PAST    = FIXED_NOW - timedelta(seconds=1)   # 1 second before now
DUE_AT_NOW  = FIXED_NOW                          # exactly at now
DUE_FUTURE  = FIXED_NOW + timedelta(seconds=1)   # 1 second after now
DUE_FAR     = datetime(2099, 12, 31, 23, 59, 0)  # obviously future, used by the normal case


# get_user_by_email layout: (user_id, role, status).
LECTURER_ROW = (2, "Lecturer", "Active")


# get_quiz layout (12 columns):
#   0 quiz_id, 1 course_id, 2 code, 3 created_by, 4 title,
#   5 time_limit_min, 6 due_at, 7 status, 8 answers_released,
#   9 created_at, 10 lecturer_id, 11 publish_at

def quiz_row(
    quiz_id: int = 42,
    title: str = "ACC101 Draft Quiz",
    time_limit_min: int = 30,
    due_at: datetime = DUE_FAR,
    status: str = "Draft",
) -> tuple:
    return (
        quiz_id,          # quiz_id
        1,                # course_id
        "ACC101",         # code
        2,                # created_by (lecturer)
        title,            # title
        time_limit_min,   # time_limit_min
        due_at,           # due_at
        status,           # status (Draft by default)
        False,            # answers_released
        datetime(2025, 1, 1, 0, 0, 0),  # created_at (fixed)
        2,                # lecturer_id — must match LECTURER_ROW[0]
        None,             # publish_at
    )


# list_questions layout:
#   (question_id, quiz_id, position, question_type, prompt,
#    accepted_answers, points)

def question_rows() -> list[tuple]:
    """One MCQ question — enough to pass the 'must have ≥1 question' guard."""
    return [
        (101, 42, 1, "MCQ", "What is 2 + 2?", None, 1),
    ]


# list_options layout for question 101:
#   (option_id, label, text, is_correct)

OPTION_ROWS = [
    (1001, "A", "3", False),
    (1002, "B", "4", True),
    (1003, "C", "5", False),
    (1004, "D", "6", False),
]