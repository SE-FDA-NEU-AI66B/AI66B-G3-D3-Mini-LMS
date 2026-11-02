"""
Mock data for US04 (Automatic grading + immediate score).

All values are hardcoded constants — nothing derived from the current
date or from a real database. The tests stay deterministic on any
machine, on any day.

The scenario set up here mirrors the acceptance criteria of US04:

    Q1  MCQ    correct option 1001        student picks 1001  → +1
    Q2  MCQ    correct option 2001        student picks 2002  →  0
    Q3  SHORT  accepted "Hà Nội"          student "  Hà Nội " → +1 (BR4 trim)
    Q4  SHORT  accepted "Paris"           student "London"    →  0

Final: 2 / 4 = 50.0 %
"""

from __future__ import annotations

from datetime import datetime


FIXED_START = datetime(2026, 1, 1, 19, 0, 0)
FIXED_SUBMIT = datetime(2026, 1, 1, 19, 25, 0)


# get_user_role_status layout: (user_id, role, status)

ACTIVE_STUDENT_ROW = (4, "Student", "Active")


# get_attempt_full layout (14 columns):
#   0 attempt_id  1 quiz_id     2 student_id  3 started_at
#   4 submitted_at 5 auto_submitted 6 score    7 total
#   8 tab_switch_count 9 title 10 code 11 time_limit_min
#   12 elapsed_seconds 13 answers_released

def unsubmitted_attempt() -> tuple:
    """An attempt that has NOT been graded yet — the normal grade path."""
    return (
        100, 1, 4, FIXED_START,
        None,        # submitted_at = None → can be graded
        False, None, None, 0,
        "ACC101 Midterm Quiz", "ACC101", 30,
        180,         # 3 minutes elapsed — well within 30-minute limit
        False,
    )


def already_submitted_attempt() -> tuple:
    """An attempt that has already been graded — should refuse re-submit."""
    return (
        100, 1, 4, FIXED_START,
        FIXED_SUBMIT,   # submitted_at set → cannot re-submit
        False, 2, 4, 0,
        "ACC101 Midterm Quiz", "ACC101", 30,
        1500,
        False,
    )


# get_questions_for_attempt layout:
#   (question_id, position, question_type, prompt, points)

QUESTION_ROWS = [
    (101, 1, "MCQ",   "Question 1", 1),
    (102, 2, "MCQ",   "Question 2", 1),
    (103, 3, "SHORT", "Question 3", 1),
    (104, 4, "SHORT", "Question 4", 1),
]


# get_grading_data layout: {question_id: (question_type, accepted_answers_json)}
# MCQ rows have accepted_answers=None; SHORT rows are JSON-encoded lists.

GRADING_DATA = {
    101: ("MCQ",   None),
    102: ("MCQ",   None),
    103: ("SHORT", '["Hà Nội"]'),
    104: ("SHORT", '["Paris"]'),
}


# get_correct_option_map: {question_id: correct_option_id}
# Only MCQ questions appear here.

CORRECT_OPTION_MAP = {
    101: 1001,   # Q1's correct option
    102: 2001,   # Q2's correct option
}


# get_answer_id_map: {question_id: answer_id}
# One answer row per question; every row gets a fixed answer_id.

ANSWER_ID_MAP = {
    101: 3001,
    102: 3002,
    103: 3003,
    104: 3004,
}


# list_answers_for_attempt layout:
#   (question_id, chosen_option_id, text_answer)
# Reflects the scenario from the docstring at the top of this file.

STUDENT_ANSWERS = [
    (101, 1001, None),          # Q1: correct MCQ
    (102, 2002, None),          # Q2: wrong MCQ (correct is 2001)
    (103, None, "  Hà Nội "),   # Q3: correct SHORT after trim + case-fold
    (104, None, "London"),      # Q4: wrong SHORT
]


# BR5 boundary table — (score, total, expected_rounded_percentage)
# These exercise `round(x, 2)` on both sides of the .xx5 threshold:
#   1/3 → 33.333… → 33.33  (rounds down, below .xx5)
#   2/3 → 66.666… → 66.67  (rounds up, above .xx5)
#   7/9 → 77.777… → 77.78  (rounds up, above .xx5)
#   8/10 → 80.0   → 80.0   (exact, 1 decimal in Python)
#   5/8 → 62.5    → 62.5   (exact, 1 decimal in Python)

BR5_BOUNDARY_CASES = [
    (1,  3,  33.33),
    (2,  3,  66.67),
    (7,  9,  77.78),
    (8, 10,  80.0),
    (5,  8,  62.5),
]