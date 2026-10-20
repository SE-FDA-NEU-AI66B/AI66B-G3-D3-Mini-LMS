"""
quiz_repository.py — SQL for quiz reads.

Only queries live here. No branching on business rules — that is the
service's job. If this module grows a decision, it belongs one layer up.
"""

from __future__ import annotations

from src.config import db as db_config
from src.models.quiz import QuizListItem

# Updated: Removed the `due_at > NOW()` filter and added the `availability` column
WALKING_SKELETON_SQL = """
SELECT q.quiz_id,
       q.title,
       c.code AS course_code,
       q.due_at,
       q.time_limit_min,
       CASE WHEN q.due_at < NOW() THEN 'overdue' ELSE 'available' END AS availability
FROM quiz q
JOIN course c     ON c.course_id = q.course_id
JOIN enrollment e ON e.course_id = c.course_id
JOIN "user" u     ON u.user_id   = e.student_id
WHERE q.status = 'Published'
  AND u.email = %s
  AND e.status = 'Active'
ORDER BY q.due_at;
"""

# New: Query for quizzes inside a specific course
COURSE_QUIZZES_SQL = """
SELECT q.quiz_id,
       q.title,
       c.code AS course_code,
       q.due_at,
       q.time_limit_min,
       CASE WHEN q.due_at < NOW() THEN 'overdue' ELSE 'available' END AS availability
FROM quiz q
JOIN course c     ON c.course_id = q.course_id
JOIN enrollment e ON e.course_id = c.course_id
JOIN "user" u     ON u.user_id   = e.student_id
WHERE q.status = 'Published'
  AND u.email = %s
  AND e.status = 'Active'
  AND c.course_id = %s
ORDER BY q.due_at;
"""

# New: Query for the student's enrolled courses
STUDENT_COURSES_SQL = """
SELECT c.course_id,
       c.code,
       c.name,
       l.full_name AS lecturer_name,
       (SELECT COUNT(*) FROM quiz q WHERE q.course_id = c.course_id AND q.status = 'Published') AS quiz_count
FROM course c
JOIN enrollment e ON e.course_id = c.course_id
JOIN "user" u     ON u.user_id = e.student_id
LEFT JOIN "user" l ON l.user_id = c.lecturer_id
WHERE u.email = %s
  AND e.status = 'Active'
ORDER BY c.code;
"""

SCHEDULED_PUBLISH_SQL = """
UPDATE quiz q
   SET status = 'Published'
 WHERE q.status IN ('Draft', 'Unpublished')
   AND q.publish_at IS NOT NULL
   AND q.publish_at <= NOW()
   AND EXISTS (SELECT 1 FROM question qq WHERE qq.quiz_id = q.quiz_id)
"""


def apply_scheduled_publishes(conn) -> int:
    """
    Flip every Draft/Unpublished quiz whose publish_at is due to Published.

    Two guards:
      * `EXISTS question` — never publish an empty quiz (mirrors US05's
        manual-publish rule that a quiz must have at least one question).
      * `publish_at <= NOW()` — only quizzes whose scheduled moment has
        arrived.

    Called at the top of every read/mutation on quiz state so the DB row
    is always honest — no background worker required.
    """
    with conn.cursor() as cur:
        cur.execute(SCHEDULED_PUBLISH_SQL)
        return cur.rowcount


def get_user_role_status(email: str) -> tuple | None:
    """
    Return (user_id, role, status) for the given email, or None.

    Used by quiz_service to gate the student-facing endpoint by role —
    a user who was promoted to Lecturer / Admin must not keep reaching
    the student quiz list just because their old enrollments still exist.
    """
    with db_config.connect() as conn, conn.cursor() as cur:
        cur.execute(
            'SELECT user_id, role, status FROM "user" WHERE email = %s',
            (email,),
        )
        return cur.fetchone()


def find_visible_quizzes(student_email: str) -> list[QuizListItem]:
    """
    Return the quizzes a student can see right now (both available and overdue).
    """
    with db_config.connect() as conn:
        apply_scheduled_publishes(conn)
        with conn.cursor() as cur:
            cur.execute(WALKING_SKELETON_SQL, (student_email,))
            rows = cur.fetchall()

    return [
        QuizListItem(
            quiz_id=quiz_id,
            title=title,
            course_code=course_code,
            due_at=due_at,
            time_limit_min=time_limit_min,
            availability=availability,
        )
        for quiz_id, title, course_code, due_at, time_limit_min, availability in rows
    ]


def find_course_quizzes(student_email: str, course_id: int) -> list[QuizListItem]:
    """
    Return the quizzes for a specific course that a student is enrolled in.
    """
    with db_config.connect() as conn:
        apply_scheduled_publishes(conn)
        with conn.cursor() as cur:
            cur.execute(COURSE_QUIZZES_SQL, (student_email, course_id))
            rows = cur.fetchall()

    return [
        QuizListItem(
            quiz_id=quiz_id,
            title=title,
            course_code=course_code,
            due_at=due_at,
            time_limit_min=time_limit_min,
            availability=availability,
        )
        for quiz_id, title, course_code, due_at, time_limit_min, availability in rows
    ]


def find_student_courses(student_email: str) -> list[dict]:
    """
    Return the list of courses the student is actively enrolled in.
    """
    with db_config.connect() as conn, conn.cursor() as cur:
        cur.execute(STUDENT_COURSES_SQL, (student_email,))
        rows = cur.fetchall()

    return [
        {
            "course_id": course_id,
            "code": code,
            "name": name,
            "lecturer_name": lecturer_name or "Unassigned",
            "quiz_count": quiz_count
        }
        for course_id, code, name, lecturer_name, quiz_count in rows
    ]