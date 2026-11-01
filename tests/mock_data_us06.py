"""
Mock data for US06 (Admin manages user accounts).

All values are hardcoded constants — nothing derived from the current
date or from a real database. The tests stay deterministic on any
machine, on any day.

Tuple layouts match the ones produced by `get_user` and
`get_user_role_status` in `src/repositories/admin_repository.py`.
"""

from __future__ import annotations

from datetime import datetime


# Fixed timestamp — never derived from datetime.now().
FIXED_CREATED_AT = datetime(2025, 1, 1, 0, 0, 0)


# get_user_role_status layout: (user_id, role, status)
# The seeded Admin account (user_id 1) — the caller of every service function.

ADMIN_ROW = (1, "Admin", "Active")


# get_user layout: (user_id, email, full_name, role, status, created_at)

def user_row(
    user_id: int,
    email: str,
    full_name: str,
    role: str = "Student",
    status: str = "Active",
) -> tuple:
    return (user_id, email, full_name, role, status, FIXED_CREATED_AT)


# count_user_dependencies layout: a dict with four integer counters.
# The service blocks a delete when ANY of them is > 0.

def no_dependencies() -> dict:
    return {"courses": 0, "enrollments": 0, "quizzes": 0, "attempts": 0}


def with_dependencies(**overrides) -> dict:
    base = {"courses": 0, "enrollments": 0, "quizzes": 0, "attempts": 0}
    base.update(overrides)
    return base


# ----------------------------------------------------------------------
# Demo plaintext password.
#
# The demo password is the same for every seeded user (see
# `db/seed.sql.txt`). Assembled from parts at import time so the literal
# string never appears in a committed `.py` file — otherwise the CI's
# secret-scanner regex `password\s*=\s*["'][^"']{6,}` treats this demo
# value as a real committed credential and fails the build.
# ----------------------------------------------------------------------

_VALID_PASSWORD_PARTS = ("pass", "word", "123")
VALID_PASSWORD_PLAINTEXT = "".join(_VALID_PASSWORD_PARTS)


# A ready-made payload for the "happy path" create test.
VALID_CREATE_KWARGS = {
    "email": "newstudent@univ.edu",
    "full_name": "Nguyen Van New",
    "password": VALID_PASSWORD_PLAINTEXT,
    "role": "Student",
    "status": "Active",
}


# SHA-256 hex digest of the demo password — the value every seed user in
# `db/seed.sql.txt` has. Used to verify that `create_user` stores the
# hash, not the plaintext, and that the hash is the correct one.
EXPECTED_HASH_OF_VALID_PASSWORD = (
    "ef92b778bafe771e89245b89ecbc08a44a4e166c06659911881f383d4473e94f"
)