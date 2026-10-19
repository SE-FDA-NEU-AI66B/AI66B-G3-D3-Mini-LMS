"""
attempt_repository.py — SQL for the student attempt flow.

All time arithmetic (elapsed_seconds, is_takeable) is pushed into SQL so
we never compare a Python `utcnow()` against a DB `NOW()` that might live
in a different timezone.
"""

from __future__ import annotations

import psycopg


# ----------------------------------------------------------------------
# Identity + quiz header
# ----------------------------------------------------------------------

def get_user_role_status(conn: psycopg.Connection, email: str) -> tuple | None:
    """Return (user_id, role, status) or None."""
    with conn.cursor() as cur:
        cur.execute(
            'SELECT user_id, role, status FROM "user" WHERE email = %s',
            (email,),
        )
        return cur.fetchone()


def get_quiz_header(conn: psycopg.Connection, quiz_id: int) -> tuple | None:
    """
    Return (quiz_id, course_id, course_code, title, time_limit_min,
    due_at, status, answers_released, is_takeable) or None.

    is_takeable = (status = 'Published' AND due_at > NOW()) — computed
    in SQL so timezone drift cannot flip the answer.
    """
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT q.quiz_id, q.course_id, c.code, q.title,
                   q.time_limit_min, q.due_at, q.status, q.answers_released,
                   (q.status = 'Published' AND q.due_at > NOW()) AS is_takeable
            FROM quiz q
            JOIN course c ON c.course_id = q.course_id
            WHERE q.quiz_id = %s
            """,
            (quiz_id,),
        )
        return cur.fetchone()


def is_active_enrolled(
    conn: psycopg.Connection, student_id: int, course_id: int
) -> bool:
    with conn.cursor() as cur:
        cur.execute(
            "SELECT 1 FROM enrollment "
            "WHERE student_id = %s AND course_id = %s AND status = 'Active'",
            (student_id, course_id),
        )
        return cur.fetchone() is not None


# ----------------------------------------------------------------------
# Attempts
# ----------------------------------------------------------------------

def get_active_attempt_id(
    conn: psycopg.Connection, student_id: int, quiz_id: int
) -> int | None:
    """Return the attempt_id of the in-progress attempt, or None (BR1)."""
    with conn.cursor() as cur:
        cur.execute(
            "SELECT attempt_id FROM attempt "
            "WHERE student_id = %s AND quiz_id = %s AND submitted_at IS NULL",
            (student_id, quiz_id),
        )
        row = cur.fetchone()
        return row[0] if row else None


def insert_attempt(
    conn: psycopg.Connection, quiz_id: int, student_id: int
) -> int:
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO attempt (quiz_id, student_id) VALUES (%s, %s) "
            "RETURNING attempt_id",
            (quiz_id, student_id),
        )
        return cur.fetchone()[0]


def get_attempt_full(conn: psycopg.Connection, attempt_id: int) -> tuple | None:
    """
    Return:
      0 attempt_id      1 quiz_id         2 student_id      3 started_at
      4 submitted_at    5 auto_submitted  6 score           7 total
      8 tab_switch_count 9 quiz_title    10 course_code    11 time_limit_min
      12 elapsed_seconds (from DB NOW()) 13 answers_released
    """
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT a.attempt_id, a.quiz_id, a.student_id, a.started_at,
                   a.submitted_at, a.auto_submitted, a.score, a.total,
                   a.tab_switch_count,
                   q.title, c.code, q.time_limit_min,
                   EXTRACT(EPOCH FROM (NOW() - a.started_at))::int AS elapsed_seconds,
                   q.answers_released
              FROM attempt a
              JOIN quiz q   ON q.quiz_id = a.quiz_id
              JOIN course c ON c.course_id = q.course_id
             WHERE a.attempt_id = %s
            """,
            (attempt_id,),
        )
        return cur.fetchone()


def increment_tab_switch(conn: psycopg.Connection, attempt_id: int) -> int:
    with conn.cursor() as cur:
        cur.execute(
            "UPDATE attempt SET tab_switch_count = tab_switch_count + 1 "
            "WHERE attempt_id = %s RETURNING tab_switch_count",
            (attempt_id,),
        )
        return cur.fetchone()[0]


def finalize_attempt(
    conn: psycopg.Connection,
    attempt_id: int,
    score: int,
    total: int,
    auto_submitted: bool,
) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE attempt
               SET submitted_at   = NOW(),
                   auto_submitted = %s,
                   score          = %s,
                   total          = %s
             WHERE attempt_id = %s
            """,
            (auto_submitted, score, total, attempt_id),
        )


def get_attempt_result_row(conn: psycopg.Connection, attempt_id: int) -> tuple | None:
    """
    Return (attempt_id, quiz_id, quiz_title, course_code, score, total,
            auto_submitted, submitted_at, answers_released) or None.
    """
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT a.attempt_id, a.quiz_id, q.title, c.code,
                   a.score, a.total, a.auto_submitted, a.submitted_at,
                   q.answers_released
              FROM attempt a
              JOIN quiz q   ON q.quiz_id = a.quiz_id
              JOIN course c ON c.course_id = q.course_id
             WHERE a.attempt_id = %s
            """,
            (attempt_id,),
        )
        return cur.fetchone()


# ----------------------------------------------------------------------
# Questions / options / answers — safe shapes for the take-quiz view
# ----------------------------------------------------------------------

def list_questions_for_attempt(conn: psycopg.Connection, quiz_id: int) -> list[tuple]:
    """
    Return (question_id, position, question_type, prompt, points) ordered
    by position. Excludes `accepted_answers` on purpose.
    """
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT question_id, position, question_type, prompt, points
              FROM question
             WHERE quiz_id = %s
             ORDER BY position
            """,
            (quiz_id,),
        )
        return cur.fetchall()


def list_options_for_attempt(conn: psycopg.Connection, question_id: int) -> list[tuple]:
    """
    Return (option_id, label, text) ordered by label. Excludes
    `is_correct` on purpose.
    """
    with conn.cursor() as cur:
        cur.execute(
            "SELECT option_id, label, text FROM option "
            "WHERE question_id = %s ORDER BY label",
            (question_id,),
        )
        return cur.fetchall()


def list_answers_for_attempt(conn: psycopg.Connection, attempt_id: int) -> list[tuple]:
    """Return (question_id, chosen_option_id, text_answer)."""
    with conn.cursor() as cur:
        cur.execute(
            "SELECT question_id, chosen_option_id, text_answer "
            "FROM answer WHERE attempt_id = %s",
            (attempt_id,),
        )
        return cur.fetchall()


def get_question_in_quiz(
    conn: psycopg.Connection, question_id: int, quiz_id: int
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


def get_option_in_question(
    conn: psycopg.Connection, option_id: int, question_id: int
) -> tuple | None:
    with conn.cursor() as cur:
        cur.execute(
            "SELECT option_id, label, text FROM option "
            "WHERE option_id = %s AND question_id = %s",
            (option_id, question_id),
        )
        return cur.fetchone()


def upsert_answer(
    conn: psycopg.Connection,
    attempt_id: int,
    question_id: int,
    chosen_option_id: int | None,
    text_answer: str | None,
) -> None:
    """Insert or replace the student's answer for one question."""
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO answer (attempt_id, question_id, chosen_option_id,
                                text_answer, is_correct)
            VALUES (%s, %s, %s, %s, FALSE)
            ON CONFLICT (attempt_id, question_id)
            DO UPDATE SET chosen_option_id = EXCLUDED.chosen_option_id,
                          text_answer      = EXCLUDED.text_answer
            """,
            (attempt_id, question_id, chosen_option_id, text_answer),
        )


# ----------------------------------------------------------------------
# Grading — only called by submit
# ----------------------------------------------------------------------

def get_grading_data(conn: psycopg.Connection, quiz_id: int) -> dict:
    """Return {question_id: (question_type, accepted_answers_json)}."""
    with conn.cursor() as cur:
        cur.execute(
            "SELECT question_id, question_type, accepted_answers "
            "FROM question WHERE quiz_id = %s",
            (quiz_id,),
        )
        return {r[0]: (r[1], r[2]) for r in cur.fetchall()}


def get_correct_option_map(conn: psycopg.Connection, quiz_id: int) -> dict:
    """Return {question_id: correct_option_id} for every MCQ of the quiz."""
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT o.question_id, o.option_id
              FROM option o
              JOIN question q ON q.question_id = o.question_id
             WHERE q.quiz_id = %s AND o.is_correct = TRUE
            """,
            (quiz_id,),
        )
        return dict(cur.fetchall())


def get_answer_id_map(conn: psycopg.Connection, attempt_id: int) -> dict:
    """Return {question_id: answer_id}."""
    with conn.cursor() as cur:
        cur.execute(
            "SELECT question_id, answer_id FROM answer WHERE attempt_id = %s",
            (attempt_id,),
        )
        return dict(cur.fetchall())


def update_answer_correctness(
    conn: psycopg.Connection, answer_id: int, is_correct: bool
) -> None:
    with conn.cursor() as cur:
        cur.execute(
            "UPDATE answer SET is_correct = %s WHERE answer_id = %s",
            (is_correct, answer_id),
        )

# ----------------------------------------------------------------------
# "One quiz at a time" enforcement
# ----------------------------------------------------------------------

def list_expired_attempts(
    conn: psycopg.Connection, student_id: int
) -> list[tuple]:
    """
    Return (attempt_id, quiz_id) of every unsubmitted attempt whose time
    window has already elapsed.

    Called by attempt_service.start_attempt to auto-submit abandoned
    attempts BEFORE checking for other active quizzes. Without this,
    closing the browser mid-quiz would leave the student locked out of
    new attempts until the timer expired client-side (which never happens
    when the browser is gone).
    """
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT a.attempt_id, a.quiz_id
              FROM attempt a
              JOIN quiz q ON q.quiz_id = a.quiz_id
             WHERE a.student_id = %s
               AND a.submitted_at IS NULL
               AND a.started_at + (q.time_limit_min * INTERVAL '1 minute') <= NOW()
            """,
            (student_id,),
        )
        return cur.fetchall()


def get_any_active_attempt(
    conn: psycopg.Connection, student_id: int
) -> tuple | None:
    """
    Return (attempt_id, quiz_id, quiz_title) of the student's current
    active attempt on ANY quiz, or None.

    Used to enforce "one quiz at a time" — a stricter reading of BR1
    than the schema index (which only guarantees one attempt per
    student-per-quiz).
    """
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT a.attempt_id, a.quiz_id, q.title
              FROM attempt a
              JOIN quiz q ON q.quiz_id = a.quiz_id
             WHERE a.student_id = %s AND a.submitted_at IS NULL
             ORDER BY a.started_at DESC
             LIMIT 1
            """,
            (student_id,),
        )
        return cur.fetchone()