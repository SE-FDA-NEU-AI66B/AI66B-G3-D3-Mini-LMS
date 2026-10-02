"""
verify_db.py — prove the walking skeleton works, from the terminal.

Runs the same SQL that powers the walking-skeleton route
(GET /api/quizzes) and prints the result.

Usage (from the repository root):
    python db/verify_db.py [student_email]
    # Default student: minhhd@univ.edu
"""

from __future__ import annotations

import pathlib
import sys

# Allow running as `python db/verify_db.py` from the repo root.
ROOT = pathlib.Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import psycopg

from src.config import db as db_config
from src.config import settings

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


def fail(msg: str) -> None:
    print(f"ERROR: {msg}", file=sys.stderr)
    sys.exit(1)


def main() -> None:
    email = sys.argv[1] if len(sys.argv) > 1 else "minhhd@univ.edu"

    print(f"Target:  {settings.describe_target()}")
    print(f"Student: {email}")
    print("Query:   walking skeleton (visible quizzes for this student)\n")

    try:
        with db_config.connect() as conn, conn.cursor() as cur:
            cur.execute(WALKING_SKELETON_SQL, (email,))
            rows = cur.fetchall()
    except psycopg.OperationalError as exc:
        fail(
            f"Cannot connect to the database: {exc}\n"
            f"Has `python db/init_db.py` been run?"
        )

    if not rows:
        print("No visible quizzes for this student.")
        print("Check that db/init_db.py has been run and the student is enrolled.")
        return

    print(f"{'ID':<4}  {'Course':<8}  {'Title':<26}  {'Due':<17}  {'Limit'}")
    print("-" * 74)
    for quiz_id, title, code, due_at, limit in rows:
        print(f"{quiz_id:<4}  {code:<8}  {title:<26}  "
              f"{due_at:%Y-%m-%d %H:%M}   {limit:>3} min")

    print(f"\n{len(rows)} quiz(zes) fetched from the database. Walking skeleton OK.")


if __name__ == "__main__":
    main()