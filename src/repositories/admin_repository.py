"""
admin_repository.py — SQL for admin user & course management.
"""

from __future__ import annotations
import psycopg


# ----------------------------------------------------------------------
# Users
# ----------------------------------------------------------------------

def list_users(conn: psycopg.Connection, role: str | None = None, status: str | None = None, q: str | None = None, user_id: int | None = None) -> list[tuple]:
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
    sql = f'SELECT user_id, email, full_name, role, status, created_at FROM "user" {clause} ORDER BY user_id'
    with conn.cursor() as cur:
        cur.execute(sql, params)
        return cur.fetchall()


def get_user(conn: psycopg.Connection, user_id: int) -> tuple | None:
    with conn.cursor() as cur:
        cur.execute('SELECT user_id, email, full_name, role, status, created_at FROM "user" WHERE user_id = %s', (user_id,))
        return cur.fetchone()


def get_user_by_email_admin(conn: psycopg.Connection, email: str) -> tuple | None:
    with conn.cursor() as cur:
        cur.execute('SELECT user_id, email, full_name, role, status, created_at FROM "user" WHERE email = %s', (email,))
        return cur.fetchone()


def get_user_role_status(conn: psycopg.Connection, email: str) -> tuple | None:
    with conn.cursor() as cur:
        cur.execute('SELECT user_id, role, status FROM "user" WHERE email = %s', (email,))
        return cur.fetchone()


def insert_user(conn: psycopg.Connection, email: str, full_name: str, password_hash: str, role: str, status: str) -> int:
    with conn.cursor() as cur:
        cur.execute('INSERT INTO "user" (email, full_name, password, role, status) VALUES (%s, %s, %s, %s, %s) RETURNING user_id',
                    (email, full_name, password_hash, role, status))
        return cur.fetchone()[0]


def update_user(conn: psycopg.Connection, user_id: int, email: str, full_name: str, role: str, status: str, password_hash: str | None = None) -> None:
    with conn.cursor() as cur:
        if password_hash is not None:
            cur.execute('UPDATE "user" SET email = %s, full_name = %s, role = %s, status = %s, password = %s WHERE user_id = %s',
                        (email, full_name, role, status, password_hash, user_id))
        else:
            cur.execute('UPDATE "user" SET email = %s, full_name = %s, role = %s, status = %s WHERE user_id = %s',
                        (email, full_name, role, status, user_id))


def delete_user(conn: psycopg.Connection, user_id: int) -> None:
    with conn.cursor() as cur:
        cur.execute('DELETE FROM "user" WHERE user_id = %s', (user_id,))


def count_user_dependencies(conn: psycopg.Connection, user_id: int) -> dict:
    with conn.cursor() as cur:
        cur.execute('''
            SELECT
              (SELECT COUNT(*) FROM course     WHERE lecturer_id = %s),
              (SELECT COUNT(*) FROM enrollment WHERE student_id  = %s),
              (SELECT COUNT(*) FROM quiz       WHERE created_by  = %s),
              (SELECT COUNT(*) FROM attempt    WHERE student_id  = %s)
        ''', (user_id, user_id, user_id, user_id))
        courses, enrollments, quizzes, attempts = cur.fetchone()
    return {"courses": courses, "enrollments": enrollments, "quizzes": quizzes, "attempts": attempts}


# ----------------------------------------------------------------------
# Courses
# ----------------------------------------------------------------------

_COURSE_SELECT = """
SELECT c.course_id, c.code, c.name,
       c.lecturer_id, u.full_name, u.email,
       (SELECT COUNT(*) FROM enrollment e WHERE e.course_id = c.course_id AND e.status = 'Active')
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


def get_course_by_code(conn: psycopg.Connection, code: str) -> tuple | None:
    with conn.cursor() as cur:
        cur.execute("SELECT course_id FROM course WHERE code = %s", (code,))
        return cur.fetchone()


def insert_course(conn: psycopg.Connection, code: str, name: str, lecturer_id: int) -> int:
    with conn.cursor() as cur:
        cur.execute("INSERT INTO course (code, name, lecturer_id) VALUES (%s, %s, %s) RETURNING course_id",
                    (code, name, lecturer_id))
        return cur.fetchone()[0]


def update_course(conn: psycopg.Connection, course_id: int, code: str, name: str, lecturer_id: int) -> None:
    with conn.cursor() as cur:
        cur.execute("UPDATE course SET code = %s, name = %s, lecturer_id = %s WHERE course_id = %s",
                    (code, name, lecturer_id, course_id))


def delete_course_cascade(conn: psycopg.Connection, course_id: int) -> None:
    """
    Permanently deletes a course and ALL its dependencies.
    Order: answer -> attempt -> option -> question -> quiz -> enrollment -> course.
    """
    with conn.cursor() as cur:
        # 1. Answers
        cur.execute("""
            DELETE FROM answer 
            WHERE attempt_id IN (
                SELECT a.attempt_id FROM attempt a
                JOIN quiz q ON q.quiz_id = a.quiz_id
                WHERE q.course_id = %s
            )
        """, (course_id,))

        # 2. Attempts
        cur.execute("""
            DELETE FROM attempt 
            WHERE quiz_id IN (SELECT quiz_id FROM quiz WHERE course_id = %s)
        """, (course_id,))

        # 3. Options
        cur.execute("""
            DELETE FROM option 
            WHERE question_id IN (
                SELECT qn.question_id FROM question qn
                JOIN quiz q ON q.quiz_id = qn.quiz_id
                WHERE q.course_id = %s
            )
        """, (course_id,))

        # 4. Questions
        cur.execute("""
            DELETE FROM question 
            WHERE quiz_id IN (SELECT quiz_id FROM quiz WHERE course_id = %s)
        """, (course_id,))

        # 5. Quizzes
        cur.execute("DELETE FROM quiz WHERE course_id = %s", (course_id,))

        # 6. Enrollments
        cur.execute("DELETE FROM enrollment WHERE course_id = %s", (course_id,))

        # 7. Course
        cur.execute("DELETE FROM course WHERE course_id = %s", (course_id,))


def count_course_dependencies(conn: psycopg.Connection, course_id: int) -> dict:
    with conn.cursor() as cur:
        cur.execute('''
            SELECT
              (SELECT COUNT(*) FROM enrollment WHERE course_id = %s),
              (SELECT COUNT(*) FROM quiz WHERE course_id = %s)
        ''', (course_id, course_id))
        enrollments, quizzes = cur.fetchone()
        return {"enrollments": enrollments, "quizzes": quizzes}


def list_course_enrollments(conn: psycopg.Connection, course_id: int) -> list[tuple]:
    with conn.cursor() as cur:
        cur.execute('''
            SELECT u.user_id, u.email, u.full_name, e.status, e.enrolled_at, u.role
              FROM enrollment e
              JOIN "user" u ON u.user_id = e.student_id
             WHERE e.course_id = %s
             ORDER BY u.full_name
        ''', (course_id,))
        return cur.fetchall()


# ----------------------------------------------------------------------
# Enrollments (US12)
# ----------------------------------------------------------------------

def get_user_by_email(conn: psycopg.Connection, email: str) -> tuple | None:
    with conn.cursor() as cur:
        cur.execute('SELECT user_id, role, status FROM "user" WHERE email = %s', (email,))
        return cur.fetchone()


def get_enrollment_status(conn: psycopg.Connection, course_id: int, student_id: int) -> str | None:
    with conn.cursor() as cur:
        cur.execute('SELECT status FROM enrollment WHERE course_id = %s AND student_id = %s', (course_id, student_id))
        row = cur.fetchone()
        return row[0] if row else None


def upsert_enrollment(conn: psycopg.Connection, course_id: int, student_id: int, status: str) -> None:
    with conn.cursor() as cur:
        cur.execute('''
            INSERT INTO enrollment (student_id, course_id, status)
            VALUES (%s, %s, %s)
            ON CONFLICT (student_id, course_id)
            DO UPDATE SET status = EXCLUDED.status
        ''', (student_id, course_id, status))