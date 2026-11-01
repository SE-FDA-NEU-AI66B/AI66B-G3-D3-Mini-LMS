"""
Automated tests for US06 — Admin manages user accounts.

Three test cases:

  TC-US06-01  normal    — an Admin creates a new Student account; the
                          response has the right fields, and the DB row
                          stores a SHA-256 hash of the password, not the
                          plaintext
  TC-US06-02  error     — creating a user with an email that already
                          exists is refused with a 409; the INSERT never
                          runs
  TC-US06-03  boundary  — the delete-permission rules are checked on
                          BOTH sides of both boundaries:
                            0 dependencies  → delete succeeds
                            ≥1 dependency   → delete blocked
                            target = admin  → delete blocked (self)

Every test runs WITHOUT a real database and WITHOUT a running server:
`db_config.connect` and the repository layer inside admin_service are
monkeypatched with canned values from mock_data_us06.py.

Run from the repository root:

    python -m pytest test/test_us06.py -v
"""

from __future__ import annotations

import hashlib
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

THIS_DIR = pathlib.Path(__file__).resolve().parent
if str(THIS_DIR) not in sys.path:
    sys.path.insert(0, str(THIS_DIR))

import pytest

from src.models.admin import UserCreateRequest
from src.services.admin_service import (
    create_user,
    delete_user,
    ConflictError,
)

import mock_data_us06


# ----------------------------------------------------------------------
# Fakes
# ----------------------------------------------------------------------

class _FakeConn:
    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        return False


def _patch_admin(monkeypatch):
    """Make `_require_admin` succeed without opening a real connection."""
    monkeypatch.setattr(
        "src.services.admin_service.db_config.connect",
        lambda: _FakeConn(),
    )
    monkeypatch.setattr(
        "src.services.admin_service.repo.get_user_role_status",
        lambda conn, email: mock_data_us06.ADMIN_ROW,
    )


# ----------------------------------------------------------------------
# TC-US06-01 — normal case
# ----------------------------------------------------------------------

def test_tc_us06_01_admin_creates_new_user(monkeypatch):
    """
    TC-US06-01 · US06 · normal

    Admin creates a new Student account with a valid email, a fresh
    password, and role="Student".

    Expect:
      * a UserAdminResponse is returned with the fields the DB stored
      * `insert_user` was called exactly once
      * the password argument passed to `insert_user` is the SHA-256
        hex digest of "password123" — NOT the plaintext and NOT some
        other hash
    """
    _patch_admin(monkeypatch)

    # No conflicting email in the DB.
    monkeypatch.setattr(
        "src.services.admin_service.repo.get_user_by_email_admin",
        lambda conn, email: None,
    )

    # Capture what `insert_user` receives so we can inspect it.
    insert_calls = []

    def fake_insert_user(conn, email, full_name, pw_hash, role, status):
        insert_calls.append(
            {"email": email, "full_name": full_name,
             "pw_hash": pw_hash, "role": role, "status": status}
        )
        return 20

    monkeypatch.setattr(
        "src.services.admin_service.repo.insert_user",
        fake_insert_user,
    )

    # The row that `get_user(conn, 20)` will fetch after the insert.
    created_row = mock_data_us06.user_row(
        user_id=20,
        email="newstudent@univ.edu",
        full_name="Nguyen Van New",
        role="Student",
        status="Active",
    )
    monkeypatch.setattr(
        "src.services.admin_service.repo.get_user",
        lambda conn, uid: created_row,
    )

    payload = UserCreateRequest(**mock_data_us06.VALID_CREATE_KWARGS)
    result = create_user("admin@univ.edu", payload)

    # Response shape
    assert result.user_id == 20
    assert result.email == "newstudent@univ.edu"
    assert result.full_name == "Nguyen Van New"
    assert result.role == "Student"
    assert result.status == "Active"

    # Insert happened exactly once, with the expected arguments.
    assert len(insert_calls) == 1
    call = insert_calls[0]
    assert call["email"] == "newstudent@univ.edu"
    assert call["full_name"] == "Nguyen Van New"
    assert call["role"] == "Student"
    assert call["status"] == "Active"

    # The stored password is a SHA-256 hex digest — not the plaintext,
    # and equal to the known hash of "password123" (verifies both that
    # hashing happened and that the *correct* algorithm was used).
    assert call["pw_hash"] != "password123"
    assert len(call["pw_hash"]) == 64
    assert all(c in "0123456789abcdef" for c in call["pw_hash"])
    assert call["pw_hash"] == mock_data_us06.EXPECTED_HASH_OF_PASSWORD123
    assert call["pw_hash"] == hashlib.sha256(b"password123").hexdigest()


# ----------------------------------------------------------------------
# TC-US06-02 — error case
# ----------------------------------------------------------------------

def test_tc_us06_02_create_rejects_duplicate_email(monkeypatch):
    """
    TC-US06-02 · US06 · error

    The admin tries to create a user with an email that already exists.
    The service must raise ConflictError(409) BEFORE any INSERT runs, so
    the DB row count does not change.
    """
    _patch_admin(monkeypatch)

    # A conflicting user already exists.
    existing_row = mock_data_us06.user_row(
        user_id=5, email="anhnv@univ.edu", full_name="Nguyen Van Anh",
    )
    monkeypatch.setattr(
        "src.services.admin_service.repo.get_user_by_email_admin",
        lambda conn, email: existing_row,
    )

    # If insert_user is reached, record it — the test should then fail.
    insert_calls = []
    monkeypatch.setattr(
        "src.services.admin_service.repo.insert_user",
        lambda *args, **kwargs: insert_calls.append(args) or 999,
    )

    payload = UserCreateRequest(
        email="anhnv@univ.edu",   # duplicate
        full_name="Someone Else",
        password="password123",
        role="Student",
        status="Active",
    )

    with pytest.raises(ConflictError) as exc_info:
        create_user("admin@univ.edu", payload)

    assert "already in use" in exc_info.value.message
    assert exc_info.value.status_code == 409
    # Nothing was inserted:
    assert insert_calls == []


# ----------------------------------------------------------------------
# TC-US06-03 — boundary on both sides of the delete rules
# ----------------------------------------------------------------------

@pytest.mark.parametrize(
    "target_user_id, dependencies, should_succeed, expected_message_fragment",
    [
        # 0 dependencies, not self → succeeds
        pytest.param(
            5,
            mock_data_us06.no_dependencies(),
            True,
            None,
            id="TC-US06-03a-no-deps-succeeds",
        ),
        # 1 dependency, not self → blocked by the dependency check
        pytest.param(
            5,
            mock_data_us06.with_dependencies(courses=1),
            False,
            "Cannot delete user",
            id="TC-US06-03b-one-dep-blocked",
        ),
        # 0 dependencies, but the target IS the admin → blocked by self-check
        pytest.param(
            1,
            mock_data_us06.no_dependencies(),
            False,
            "cannot delete your own account",
            id="TC-US06-03c-self-delete-blocked",
        ),
    ],
)
def test_tc_us06_03_delete_boundaries(
    monkeypatch,
    target_user_id,
    dependencies,
    should_succeed,
    expected_message_fragment,
):
    """
    TC-US06-03 · US06 · boundary (both sides of two rules)

    The delete-permission rules have two independent boundaries:

      * dependency count: 0 → allowed, ≥1 → blocked
      * identity:         other user → allowed, self → blocked

    This parametrized test covers both sides of both boundaries:

        zero dependencies, other user → delete succeeds
        one dependency,   other user → blocked (dependency rule)
        zero dependencies, self       → blocked (self-protection rule)
    """
    _patch_admin(monkeypatch)

    target_row = mock_data_us06.user_row(
        user_id=target_user_id,
        email="someone@univ.edu",
        full_name="Some One",
    )
    monkeypatch.setattr(
        "src.services.admin_service.repo.get_user",
        lambda conn, uid: target_row if uid == target_user_id else None,
    )
    monkeypatch.setattr(
        "src.services.admin_service.repo.count_user_dependencies",
        lambda conn, uid: dependencies,
    )

    delete_calls = []
    monkeypatch.setattr(
        "src.services.admin_service.repo.delete_user",
        lambda conn, uid: delete_calls.append(uid),
    )

    if should_succeed:
        delete_user("admin@univ.edu", target_user_id)
        assert delete_calls == [target_user_id]
    else:
        with pytest.raises(ConflictError) as exc_info:
            delete_user("admin@univ.edu", target_user_id)
        assert exc_info.value.status_code == 409
        assert expected_message_fragment in exc_info.value.message
        # The delete was NOT performed:
        assert delete_calls == []