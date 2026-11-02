"""
Mock data for US03 (Student takes quiz with countdown timer).

All values are hardcoded constants — nothing derived from the current
date or from a real database. The tests stay deterministic on any
machine, on any day.

Tuple layouts match the ones produced by the real SQL queries in
`src/repositories/attempt_repository.py`.
"""

from __future__ import annotations

from datetime import datetime


# Fixed timestamps — never derived from datetime.now().

FUTURE_DUE   = datetime(2099, 12, 31, 23, 59, 0)
FIXED_NOW    = datetime(2026,  1,  1, 19,  0, 0)


# get_user_role_status layout: (user_id, role, status)

ACTIVE_STUDENT_ROW = (4, "Student", "Active")


# get_quiz_header layout:
#   (quiz_id, course_id, code, title, time_limit_min, due_at,
#    status, answers_released, is_takeable)

def quiz_header(
    quiz_id: int = 1,
    course_id: int = 1,
    code: str = "ACC101",
    title: str = "ACC101 Midterm Quiz",
    time_limit_min: int = 30,
    status: str = "Published",
    is_takeable: bool = True,
) -> tuple:
    return (
        quiz_id, course_id, code, title, time_limit_min,
        FUTURE_DUE, status, False, is_takeable,
    )


# get_attempt_full layout:
#   0 attempt_id  1 quiz_id     2 student_id  3 started_at
#   4 submitted_at 5 auto_submitted 6 score    7 total
#   8 tab_switch_count 9 title 10 code 11 time_limit_min
#   12 elapsed_seconds 13 answers_released

def attempt_row(
    attempt_id: int = 100,
    quiz_id: int = 1,
    student_id: int = 4,
    title: str = "ACC101 Midterm Quiz",
    code: str = "ACC101",
    time_limit_min: int = 30,
    elapsed_seconds: int = 0,
    submitted_at=None,
    tab_switch_count: int = 0,
) -> tuple:
    return (
        attempt_id, quiz_id, student_id, FIXED_NOW,
        submitted_at, False, None, None, tab_switch_count,
        title, code, time_limit_min, elapsed_seconds, False,
    )


# Question rows returned by get_questions_for_attempt (one MCQ, one SHORT).

def question_rows() -> list[tuple]:
    return [
        (101, 1, "MCQ",   "What is 2 + 2?",      1),
        (102, 2, "SHORT", "Name the capital city.", 1),
    ]


# Options for the MCQ question (question_id = 101).

MCQ_OPTIONS = [
    (1001, "A", "Option A"),
    (1002, "B", "Option B"),
    (1003, "C", "Option C"),
    (1004, "D", "Option D"),
]


# A single question row for the "save answer" boundary test (BR3).

def single_mcq_question_row() -> tuple:
    """Layout: (question_id, quiz_id, position, question_type, prompt,
                accepted_answers, points)"""
    return (101, 1, 1, "MCQ", "What is 2 + 2?", None, 1)


# A single option row for get_option_in_question.

SINGLE_MCQ_OPTION_ROW = (1001, "A", "Option A")


# A different quiz that is already active — used by TC-US03-02.

OTHER_ACTIVE_ATTEMPT = (99, 2, "ACC201 Midterm Quiz")