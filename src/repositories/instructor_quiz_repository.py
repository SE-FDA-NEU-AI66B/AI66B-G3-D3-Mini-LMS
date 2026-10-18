"""
instructor_quiz_repository.py — SQL for lecturer-side quiz CRUD.

Only SQL lives here. Each function receives an open connection from the
service layer so that a multi-statement operation (create quiz + options,
delete quiz + questions) either commits as a whole or rolls back as a
whole. No business rules live here — that is the service's job.
"""

from __future__ import annotations

from datetime import datetime

import psycopg

# ----------------------------------------------------------------------
# Users & courses — ownership lookups
# ----------------------------------------------------------------------

def get_user_by_email(conn: psycopg.Connection, email: str) -> tuple | None:
    """Return (user_id, role, status) or None."""
    with conn.cursor() as cur:
        cur.execute(
            'SELECT user_id, role, status FROM "user" WHERE email = %s',
            (email,),
        )
        return cur.fetchone()


def get_user_full_by_email(
    conn: psycopg.Connection, email: str
) -> tuple | None:
    """
    Return (user_id, email, full_name, password, role, status) or None.

    Used only by the auth service — the plain `get_user_by_email` above
    is kept password-free so callers that never need the hash cannot
    accidentally log it.
    """
    with conn.cursor() as cur:
        cur.execute(
            'SELECT user_id, email, full_name, password, role, status '
            'FROM "user" WHERE email = %s',
            (email,),
        )
        return cur.fetchone()


def get_course(conn: psycopg.Connection, course_id: int) -> tuple | None:
    """Return (course_id, code, name, lecturer_id) or None."""
    with conn.cursor() as cur:
        cur.execute(
            "SELECT course_id, code, name, lecturer_id "
            "FROM course WHERE course_id = %s",
            (course_id,),
        )
        return cur.fetchone()


def list_courses_for_lecturer(
    conn: psycopg.Connection, lecturer_id: int
) -> list[tuple]:
    """Return (course_id, code, name) for courses assigned to this lecturer."""
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT course_id, code, name
              FROM course
             WHERE lecturer_id = %s
             ORDER BY code
            """,
            (lecturer_id,),
        )
        return cur.fetchall()

# ----------------------------------------------------------------------
# Quizzes
# ----------------------------------------------------------------------

_QUIZ_SELECT = """
SELECT q.quiz_id, q.course_id, c.code, q.created_by, q.title,
       q.time_limit_min, q.due_at, q.status, q.answers_released,
       q.created_at, c.lecturer_id, q.publish_at
FROM quiz q
JOIN course c ON c.course_id = q.course_id
"""


def get_quiz(conn: psycopg.Connection, quiz_id: int) -> tuple | None:
    """Return the quiz row joined with its course (for ownership checks)."""
    with conn.cursor() as cur:
        cur.execute(_QUIZ_SELECT + " WHERE q.quiz_id = %s", (quiz_id,))
        return cur.fetchone()


def list_quizzes_for_lecturer(
    conn: psycopg.Connection, lecturer_id: int
) -> list[tuple]:
    """
    Return (quiz_id, course_id, course_code, title, time_limit_min,
    due_at, status, created_at, question_count, publish_at) for every quiz
    whose owning course is assigned to this lecturer.
    """
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT q.quiz_id, q.course_id, c.code, q.title, q.time_limit_min,
                   q.due_at, q.status, q.created_at,
                   (SELECT COUNT(*) FROM question WHERE quiz_id = q.quiz_id),
                   q.publish_at
            FROM quiz q
            JOIN course c ON c.course_id = q.course_id
            WHERE c.lecturer_id = %s
            ORDER BY q.created_at DESC, q.quiz_id DESC
            """,
            (lecturer_id,),
        )
        return cur.fetchall()


def insert_quiz(
    conn: psycopg.Connection,
    course_id: int,
    created_by: int,
    title: str,
    time_limit_min: int,
    due_at: datetime,
    publish_at: datetime,
) -> int:
    """Insert a Draft quiz and return its new quiz_id."""
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO quiz
                (course_id, created_by, title, time_limit_min, due_at,
                 publish_at, status)
            VALUES (%s, %s, %s, %s, %s, %s, 'Draft')
            RETURNING quiz_id
            """,
            (course_id, created_by, title, time_limit_min, due_at, publish_at),
        )
        return cur.fetchone()[0]


def update_quiz(
    conn: psycopg.Connection,
    quiz_id: int,
    title: str,
    time_limit_min: int,
    due_at: datetime,
    publish_at: datetime,
) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE quiz
               SET title = %s, time_limit_min = %s,
                   due_at = %s, publish_at = %s
             WHERE quiz_id = %s
            """,
            (title, time_limit_min, due_at, publish_at, quiz_id),
        )


def count_attempts(conn: psycopg.Connection, quiz_id: int) -> int:
    with conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM attempt WHERE quiz_id = %s", (quiz_id,))
        return cur.fetchone()[0]


def delete_quiz_cascade(conn: psycopg.Connection, quiz_id: int) -> None:
    """
    Delete a quiz together with its questions and options.

    The caller (service) has already confirmed there are no attempts, so
    no answer rows reference these questions/options. Order matters:
    option → question → quiz, because none of the FKs use ON DELETE
    CASCADE in schema.sql.
    """
    with conn.cursor() as cur:
        cur.execute(
            """
            DELETE FROM option
             WHERE question_id IN
                   (SELECT question_id FROM question WHERE quiz_id = %s)
            """,
            (quiz_id,),
        )
        cur.execute("DELETE FROM question WHERE quiz_id = %s", (quiz_id,))
        cur.execute("DELETE FROM quiz     WHERE quiz_id = %s", (quiz_id,))


def set_quiz_status(conn: psycopg.Connection, quiz_id: int, status: str) -> None:
    """Change a quiz's status. Caller is responsible for validating the transition."""
    with conn.cursor() as cur:
        cur.execute(
            "UPDATE quiz SET status = %s, publish_at = NULL WHERE quiz_id = %s",
            (status, quiz_id),
        )


# ----------------------------------------------------------------------
# Questions & options
# ----------------------------------------------------------------------

def list_questions(conn: psycopg.Connection, quiz_id: int) -> list[tuple]:
    """Return (question_id, quiz_id, position, question_type, prompt,
    accepted_answers, points) ordered by position."""
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT question_id, quiz_id, position, question_type, prompt,
                   accepted_answers, points
              FROM question
             WHERE quiz_id = %s
             ORDER BY position
            """,
            (quiz_id,),
        )
        return cur.fetchall()


def get_question(
    conn: psycopg.Connection, quiz_id: int, question_id: int
) -> tuple | None:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT question_id, quiz_id, position, question_type, prompt,
                   accepted_answers, points
              FROM question
             WHERE question_id = %s AND quiz_id = %s
            """,
            (question_id, quiz_id),
        )
        return cur.fetchone()


def list_options(conn: psycopg.Connection, question_id: int) -> list[tuple]:
    """Return (option_id, label, text, is_correct) ordered by label."""
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT option_id, label, text, is_correct
              FROM option
             WHERE question_id = %s
             ORDER BY label
            """,
            (question_id,),
        )
        return cur.fetchall()


def next_position(conn: psycopg.Connection, quiz_id: int) -> int:
    with conn.cursor() as cur:
        cur.execute(
            "SELECT COALESCE(MAX(position), 0) + 1 FROM question WHERE quiz_id = %s",
            (quiz_id,),
        )
        return cur.fetchone()[0]


def position_exists(conn: psycopg.Connection, quiz_id: int, position: int) -> bool:
    with conn.cursor() as cur:
        cur.execute(
            "SELECT 1 FROM question WHERE quiz_id = %s AND position = %s",
            (quiz_id, position),
        )
        return cur.fetchone() is not None


def insert_question(
    conn: psycopg.Connection,
    quiz_id: int,
    position: int,
    question_type: str,
    prompt: str,
    accepted_answers_json: str | None,
) -> int:
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO question
                (quiz_id, position, question_type, prompt, accepted_answers, points)
            VALUES (%s, %s, %s, %s, %s, 1)
            RETURNING question_id
            """,
            (quiz_id, position, question_type, prompt, accepted_answers_json),
        )
        return cur.fetchone()[0]


def update_question(
    conn: psycopg.Connection,
    question_id: int,
    question_type: str,
    prompt: str,
    accepted_answers_json: str | None,
) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE question
               SET question_type = %s,
                   prompt = %s,
                   accepted_answers = %s
             WHERE question_id = %s
            """,
            (question_type, prompt, accepted_answers_json, question_id),
        )


def delete_question(conn: psycopg.Connection, question_id: int) -> None:
    with conn.cursor() as cur:
        cur.execute("DELETE FROM question WHERE question_id = %s", (question_id,))


def delete_options_for_question(conn: psycopg.Connection, question_id: int) -> None:
    with conn.cursor() as cur:
        cur.execute("DELETE FROM option WHERE question_id = %s", (question_id,))


def insert_option(
    conn: psycopg.Connection,
    question_id: int,
    label: str,
    text: str,
    is_correct: bool,
) -> int:
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO option (question_id, label, text, is_correct)
            VALUES (%s, %s, %s, %s)
            RETURNING option_id
            """,
            (question_id, label, text, is_correct),
        )
        return cur.fetchone()[0]