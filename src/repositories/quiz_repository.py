"""
quiz_repository.py — SQL for quiz reads.

Only queries live here. No branching on business rules — that is the
service's job. If this module grows a decision, it belongs one layer up.
"""

from __future__ import annotations

from src.config import db as db_config
from src.models.quiz import QuizListItem
import psycopg

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
    Return the quizzes a student can see right now.

    "Visible" is defined by BR6: Published + before due date + enrolled.
    The repository does not decide this — the WHERE clause simply applies
    the rule that the service has already confirmed is in force.
    """
    with db_config.connect() as conn:
        # Any scheduled-publish quizzes whose time has come are flipped
        # here, in the same transaction as the visibility SELECT.
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
        )
        for quiz_id, title, course_code, due_at, time_limit_min in rows
    ]
    
def get_quiz_with_questions_for_taking(conn: psycopg.Connection, quiz_id: int) -> tuple | None:
    """Lấy thông tin quiz và toàn bộ câu hỏi/đáp án để render."""
    with conn.cursor() as cur:
        cur.execute("SELECT quiz_id, title, time_limit_min, status, due_at FROM quiz WHERE quiz_id = %s", (quiz_id,))
        quiz = cur.fetchone()
        if not quiz: return None
        
        cur.execute("SELECT question_id, position, question_type, prompt, points FROM question WHERE quiz_id = %s ORDER BY position", (quiz_id,))
        questions = cur.fetchall()
        
        questions_with_options = []
        for q in questions:
            q_id = q[0]
            if q[2] == 'MCQ':
                cur.execute("SELECT option_id, label, text FROM option WHERE question_id = %s ORDER BY label", (q_id,))
                options = cur.fetchall()
            else:
                options = []
            questions_with_options.append((q, options))
            
        return (quiz, questions_with_options)

def create_attempt(conn: psycopg.Connection, quiz_id: int, student_id: int) -> int:
    """Tạo attempt mới."""
    with conn.cursor() as cur:
        cur.execute("INSERT INTO attempt (quiz_id, student_id) VALUES (%s, %s) RETURNING attempt_id", (quiz_id, student_id))
        return cur.fetchone()[0]

def save_graded_answers(conn: psycopg.Connection, attempt_id: int, answers: list[dict], score: int, total: int, auto_submitted: bool) -> None:
    """Lưu câu trả lời và cập nhật điểm."""
    with conn.cursor() as cur:
        for ans in answers:
            cur.execute(
                """
                INSERT INTO answer (attempt_id, question_id, chosen_option_id, text_answer, is_correct)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (attempt_id, ans['question_id'], ans.get('chosen_option_id'), ans.get('text_answer'), ans['is_correct'])
            )
        cur.execute(
            "UPDATE attempt SET submitted_at = NOW(), score = %s, total = %s, auto_submitted = %s WHERE attempt_id = %s",
            (score, total, auto_submitted, attempt_id)
        )