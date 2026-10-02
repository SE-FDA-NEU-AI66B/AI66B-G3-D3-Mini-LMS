"""
quiz_repository.py — SQL for quiz reads.

Only queries live here. No branching on business rules — that is the
service's job. If this module grows a decision, it belongs one layer up.
"""

from __future__ import annotations

from src.config import db as db_config
from src.models.quiz import QuizListItem


WALKING_SKELETON_SQL = """
SELECT q.quiz_id,
       q.title,
       c.code AS course_code,
       q.due_at,
       q.time_limit_min
FROM quiz q
JOIN course c     ON c.course_id = q.course_id
JOIN enrollment e ON e.course_id = c.course_id
JOIN "user" u     ON u.user_id   = e.student_id
WHERE q.status = 'Published'
  AND q.due_at > NOW()
  AND u.email = %s
  AND e.status = 'Active'
ORDER BY q.due_at;
"""


def find_visible_quizzes(student_email: str) -> list[QuizListItem]:
    """
    Return the quizzes a student can see right now.

    "Visible" is defined by BR6: Published + before due date + enrolled.
    The repository does not decide this — the WHERE clause simply applies
    the rule that the service has already confirmed is in force.
    """
    with db_config.connect() as conn, conn.cursor() as cur:
        cur.execute(WALKING_SKELETON_SQL, (student_email,))
        rows = cur.fetchall()

    return [
        QuizListItem(
            quiz_id=quiz_id,
            title=title,
            course_code=course_code,
            due_at=due_at,
            time_limit_min=time_limit_min,
        )
        for quiz_id, title, course_code, due_at, time_limit_min in rows
    ]