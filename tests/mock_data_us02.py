"""
Mock data for US02 (Student sees available quizzes) test cases.

All values are hardcoded constants — not generated, not read from a file,
not derived from the current date. The tests stay deterministic on any
machine, on any day.

QuizListItem is imported from src.models.quiz so the fixtures are the
same shape the real repository returns.
"""

from __future__ import annotations

from datetime import datetime

from src.models.quiz import QuizListItem


# Fixed timestamps — never derived from datetime.now().
PAST_DUE   = datetime(2024,  1,  1, 23, 59, 0)   # any quiz with this is 'overdue'
FUTURE_DUE = datetime(2099, 12, 31, 23, 59, 0)   # any quiz with this is 'available'


# Tuples returned by get_user_role_status — layout: (user_id, role, status)

ACTIVE_STUDENT_ROW   = (4, "Student",  "Active")
DISABLED_STUDENT_ROW = (5, "Student",  "Disabled")
ACTIVE_LECTURER_ROW  = (2, "Lecturer", "Active")
ACTIVE_ADMIN_ROW     = (1, "Admin",    "Active")


# QuizListItem instances as they'd be built by find_visible_quizzes.
# Two with a future due date (available) and two already past due (overdue).

AVAILABLE_QUIZZES = [
    QuizListItem(
        quiz_id=1,
        title="ACC101 Midterm Quiz",
        course_code="ACC101",
        due_at=FUTURE_DUE,
        time_limit_min=30,
        availability="available",
    ),
    QuizListItem(
        quiz_id=5,
        title="ACC201 Midterm Quiz",
        course_code="ACC201",
        due_at=FUTURE_DUE,
        time_limit_min=30,
        availability="available",
    ),
]

OVERDUE_QUIZZES = [
    QuizListItem(
        quiz_id=13,
        title="ACC101 Overdue Quiz",
        course_code="ACC101",
        due_at=PAST_DUE,
        time_limit_min=15,
        availability="overdue",
    ),
    QuizListItem(
        quiz_id=14,
        title="ACC201 Overdue Quiz",
        course_code="ACC201",
        due_at=PAST_DUE,
        time_limit_min=15,
        availability="overdue",
    ),
]

MIXED_QUIZZES = AVAILABLE_QUIZZES + OVERDUE_QUIZZES