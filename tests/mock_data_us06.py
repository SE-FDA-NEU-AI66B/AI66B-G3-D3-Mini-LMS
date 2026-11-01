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


# A ready-made payload for the "happy path" create test.
VALID_CREATE_KWARGS = {
    "email": "newstudent@univ.edu",
    "full_name": "Nguyen Van New",
    "password": "password123",
    "role": "Student",
    "status": "Active",
}


# SHA-256 hex digest of "password123" — the value every seed user in
# `db/seed.sql.txt` has. Used to verify that `create_user` stores the
# hash, not the plaintext, and to prove the hash is the *correct* one.
EXPECTED_HASH_OF_PASSWORD123 = (
    "ef92b778bafe771e89245b89ecbc08a44a4e166c06659911881f383d4473e94f"
)