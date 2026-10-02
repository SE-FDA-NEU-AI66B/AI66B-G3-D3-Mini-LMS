"""
init_db.py — initialise the Mini-LMS database.

Steps:
  1. Read DB config from src/config (loaded from .env).
  2. Create the target database if it does not exist.
  3. Run db/schema.sql — drops and recreates every table and enum.
  4. Run db/seed.sql   — populates the database with sample data.
  5. Print a short row-count summary.

Usage (from the repository root):
    python db/init_db.py
"""

from __future__ import annotations

import pathlib
import sys

# Allow running as `python db/init_db.py` from the repo root.
ROOT = pathlib.Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import psycopg

from src.config import db as db_config
from src.config import settings

SCHEMA_FILE = ROOT / "db" / "schema.sql.txt"
SEED_FILE = ROOT / "db" / "seed.sql.txt"


def fail(msg: str) -> None:
    print(f"ERROR: {msg}", file=sys.stderr)
    sys.exit(1)


def ensure_database_exists() -> None:
    """Create the target database if it is missing, using the 'postgres' DB."""
    target = settings.DB_NAME
    try:
        db_config.connect().close()
        return  # Target exists.
    except psycopg.OperationalError:
        pass

    print(f"Database '{target}' not found — creating it ...")
    try:
        with (
            db_config.connect(target_db="postgres", autocommit=True) as conn,
            conn.cursor() as cur,
        ):
            cur.execute(f'CREATE DATABASE "{target}"')
    except psycopg.errors.DuplicateDatabase:
        pass
    except psycopg.Error as exc:
        fail(
            f"Could not create database '{target}': {exc}\n"
            f"Create it manually:  createdb {target}"
        )


def run_sql_file(conn: psycopg.Connection, path: pathlib.Path) -> None:
    if not path.exists():
        fail(f"Missing file: {path}")
    print(f"  → {path.relative_to(ROOT)}")
    statements = [s.strip() for s in path.read_text(encoding="utf-8").split(";") if s.strip()]
    with conn.cursor() as cur:
        for stmt in statements:
            cur.execute(stmt)


def summarise(conn: psycopg.Connection) -> dict[str, int]:
    with conn.cursor() as cur:
        cur.execute("""
            SELECT
              (SELECT COUNT(*) FROM "user")     AS users,
              (SELECT COUNT(*) FROM course)     AS courses,
              (SELECT COUNT(*) FROM enrollment) AS enrollments,
              (SELECT COUNT(*) FROM quiz)       AS quizzes,
              (SELECT COUNT(*) FROM question)   AS questions,
              (SELECT COUNT(*) FROM option)     AS options,
              (SELECT COUNT(*) FROM attempt)    AS attempts,
              (SELECT COUNT(*) FROM answer)     AS answers
        """)
        row = cur.fetchone()
    keys = ["users", "courses", "enrollments", "quizzes",
            "questions", "options", "attempts", "answers"]
    return dict(zip(keys, row))


def main() -> None:
    print(f"Target: {settings.describe_target()}\n")

    ensure_database_exists()

    print("Running schema and seed ...")
    with db_config.connect() as conn:
        run_sql_file(conn, SCHEMA_FILE)
        run_sql_file(conn, SEED_FILE)
        conn.commit()
        counts = summarise(conn)

    print("\nDatabase initialised.")
    for key, value in counts.items():
        print(f"  {key:<12}: {value}")


if __name__ == "__main__":
    main()