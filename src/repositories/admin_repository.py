"""
admin_repository.py — SQL for admin user & course management.

Only SQL lives here. No business rules — that is the service's job.
"""

from __future__ import annotations

import psycopg


# ----------------------------------------------------------------------
# Users
# ----------------------------------------------------------------------

def list_users(
    conn: psycopg.Connection,
    role: str | None = None,
    status: str | None = None,
    q: str | None = None,
    user_id: int | None = None,
) -> list[tuple]:
    """
    Return (user_id, email, full_name, role, status, created_at).

    All filters are optional and combined with AND.
    """
    where: list[str] = []
    params: list = []
    if role:
        where.append("role = %s")
        params.append(role)
    if status:
        where.append("status = %s")
        params.append(status)
    if user_id is not None:
        where.append("user_id = %s")
        params.append(user_id)
    if q:
        where.append("(email ILIKE %s OR full_name ILIKE %s)")
        like = f"%{q}%"
        params.extend([like, like])

    clause = ("WHERE " + " AND ".join(where)) if where else ""
    sql = f"""
        SELECT user_id, email, full_name, role, status, created_at
          FROM "user"
          {clause}
         ORDER BY user_id
    """
    with conn.cursor() as cur:
        cur.execute(sql, params)
        return cur.fetchall()


def get_user(conn: psycopg.Connection, user_id: int) -> tuple | None:
    """Return (user_id, email, full_name, role, status, created_at)."""
    with conn.cursor() as cur:
        cur.execute(
            'SELECT user_id, email, full_name, role, status, created_at '
            'FROM "user" WHERE user_id = %s',
            (user_id,),
        )
        return cur.fetchone()


def get_user_by_email_admin(conn: psycopg.Connection, email: str) -> tuple | None:
    """Admin variant: does not expose the password hash."""
    with conn.cursor() as cur:
        cur.execute(
            'SELECT user_id, email, full_name, role, status, created_at '
            'FROM "user" WHERE email = %s',
            (email,),
        )
        return cur.fetchone()


def get_user_role_status(
    conn: psycopg.Connection, email: str
) -> tuple | None:
    """Return (user_id, role, status) or None — used for admin-auth check."""
    with conn.cursor() as cur:
        cur.execute(
            'SELECT user_id, role, status FROM "user" WHERE email = %s',
            (email,),
        )
        return cur.fetchone()


def insert_user(
    conn: psycopg.Connection,
    email: str,
    full_name: str,
    password_hash: str,
    role: str,
    status: str,
) -> int:
    with conn.cursor() as cur:
        cur.execute(
            '''
            INSERT INTO "user" (email, full_name, password, role, status)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING user_id
            ''',
            (email, full_name, password_hash, role, status),
        )
        return cur.fetchone()[0]


def update_user(
    conn: psycopg.Connection,
    user_id: int,
    email: str,
    full_name: str,
    role: str,
    status: str,
    password_hash: str | None = None,
) -> None:
    """Updates the profile fields. password_hash=None → keep existing password."""
    with conn.cursor() as cur:
        if password_hash is not None:
            cur.execute(
                '''
                UPDATE "user"
                   SET email = %s,
                       full_name = %s,
                       role = %s,
                       status = %s,
                       password = %s
                 WHERE user_id = %s
                ''',
                (email, full_name, role, status, password_hash, user_id),
            )
        else:
            cur.execute(
                '''
                UPDATE "user"
                   SET email = %s,
                       full_name = %s,
                       role = %s,
                       status = %s
                 WHERE user_id = %s
                ''',
                (email, full_name, role, status, user_id),
            )


def delete_user(conn: psycopg.Connection, user_id: int) -> None:
    with conn.cursor() as cur:
        cur.execute('DELETE FROM "user" WHERE user_id = %s', (user_id,))


def count_user_dependencies(conn: psycopg.Connection, user_id: int) -> dict:
    """
    Count rows that reference this user. Used to block deletes that would
    violate FKs — or silently destroy data the admin shouldn't be able to
    wipe from the accounts screen.
    """
    with conn.cursor() as cur:
        cur.execute(
            '''
            SELECT
              (SELECT COUNT(*) FROM course     WHERE lecturer_id = %s),
              (SELECT COUNT(*) FROM enrollment WHERE student_id  = %s),
              (SELECT COUNT(*) FROM quiz       WHERE created_by  = %s),
              (SELECT COUNT(*) FROM attempt    WHERE student_id  = %s)
            ''',
            (user_id, user_id, user_id, user_id),
        )
        courses, enrollments, quizzes, attempts = cur.fetchone()
    return {
        "courses": courses,
        "enrollments": enrollments,
        "quizzes": quizzes,
        "attempts": attempts,
    }


# ----------------------------------------------------------------------
# Courses (read-only)
# ----------------------------------------------------------------------

_COURSE_SELECT = """
SELECT c.course_id, c.code, c.name,
       c.lecturer_id, u.full_name, u.email,
       (SELECT COUNT(*) FROM enrollment e
         WHERE e.course_id = c.course_id AND e.status = 'Active')
  FROM course c
  JOIN "user" u ON u.user_id = c.lecturer_id
"""


def list_courses_admin(conn: psycopg.Connection) -> list[tuple]:
    with conn.cursor() as cur:
        cur.execute(_COURSE_SELECT + " ORDER BY c.code")
        return cur.fetchall()


def get_course_admin(conn: psycopg.Connection, course_id: int) -> tuple | None:
    with conn.cursor() as cur:
        cur.execute(_COURSE_SELECT + " WHERE c.course_id = %s", (course_id,))
        return cur.fetchone()


def list_course_enrollments(
    conn: psycopg.Connection, course_id: int
) -> list[tuple]:
    """
    Return (user_id, email, full_name, enrollment_status, enrolled_at, role)
    for every enrollment row of the course (including 'Removed').

    `role` is the user's *global* role — the roster uses it to make it
    visible when a promoted user still has an enrollment row.
    """
    with conn.cursor() as cur:
        cur.execute(
            '''
            SELECT u.user_id, u.email, u.full_name, e.status, e.enrolled_at, u.role
              FROM enrollment e
              JOIN "user" u ON u.user_id = e.student_id
             WHERE e.course_id = %s
             ORDER BY u.full_name
            ''',
            (course_id,),
        )
        return cur.fetchall()
    
# ----------------------------------------------------------------------
# Enrollments (Task #67)
# ----------------------------------------------------------------------

def get_user_by_email(conn: psycopg.Connection, email: str) -> tuple | None:
    """Return (user_id, role, status)."""
    with conn.cursor() as cur:
        cur.execute(
            'SELECT user_id, role, status FROM "user" WHERE email = %s',
            (email,)
        )
        return cur.fetchone()

def get_enrollment_status(conn: psycopg.Connection, course_id: int, student_id: int) -> str | None:
    """Return 'Active' | 'Removed' | None."""
    with conn.cursor() as cur:
        cur.execute(
            'SELECT status FROM enrollment WHERE course_id = %s AND student_id = %s',
            (course_id, student_id)
        )
        row = cur.fetchone()
        return row[0] if row else None

def upsert_enrollment(conn: psycopg.Connection, course_id: int, student_id: int, status: str) -> None:
    """Insert or Update enrollment status."""
    with conn.cursor() as cur:
        cur.execute(
            '''
            INSERT INTO enrollment (student_id, course_id, status)
            VALUES (%s, %s, %s)
            ON CONFLICT (student_id, course_id)
            DO UPDATE SET status = EXCLUDED.status
            ''',
            (student_id, course_id, status)
        )