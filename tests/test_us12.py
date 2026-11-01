"""
Automated tests for US12 — Admin enrolls students into a course.

Three test cases:

  TC-US12-01  normal    — the admin enrolls a valid Active Student into
                          a course; `upsert_enrollment` is called once
                          with status="Active"
  TC-US12-02  error     — the target account is a Lecturer (not a
                          Student); the service refuses with 422 and
                          never writes an enrollment row
  TC-US12-03  boundary  — both sides of two enrollment rules, plus the
                          account-status boundary:
                            no prior enrollment       → succeeds (new)
                            already Active            → 409 (blocked)
                            previously Removed        → succeeds (restored)
                            disabled account          → 422 (blocked)

Every test runs WITHOUT a real database and WITHOUT a running server:
`db_config.connect` and the repository layer inside admin_service are
monkeypatched with canned values from mock_data_us12.py.

Run from the repository root:

    python -m pytest test/test_us12.py -v
"""

from __future__ import annotations

import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

THIS_DIR = pathlib.Path(__file__).resolve().parent
if str(THIS_DIR) not in sys.path:
    sys.path.insert(0, str(THIS_DIR))

import pytest

from src.services.admin_service import (
    add_enrollment,
    ConflictError,
    ValidationError,
)

import mock_data_us12


# ----------------------------------------------------------------------
# Fakes
# ----------------------------------------------------------------------

class _FakeConn:
    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        return False


def _patch_admin_auth(monkeypatch):
    """Make `_require_admin` succeed without a real DB."""
    monkeypatch.setattr(
        "src.services.admin_service.db_config.connect",
        lambda: _FakeConn(),
    )
    monkeypatch.setattr(
        "src.services.admin_service.repo.get_user_role_status",
        lambda conn, email: mock_data_us12.ADMIN_AUTH_ROW,
    )


def _patch_course_and_user(monkeypatch, *, user_row, existing_status):
    """
    Wire up the two lookups `add_enrollment` performs before it decides
    what to do, plus the current enrollment state.

    Returns a list `upsert_calls` that captures every call to
    `repo.upsert_enrollment` — the assertion hooks into it.
    """
    monkeypatch.setattr(
        "src.services.admin_service.repo.get_course_admin",
        lambda conn, cid: mock_data_us12.COURSE_ROW,
    )
    monkeypatch.setattr(
        "src.services.admin_service.repo.get_user_by_email",
        lambda conn, email: user_row,
    )
    monkeypatch.setattr(
        "src.services.admin_service.repo.get_enrollment_status",
        lambda conn, cid, uid: existing_status,
    )

    upsert_calls = []
    monkeypatch.setattr(
        "src.services.admin_service.repo.upsert_enrollment",
        lambda conn, cid, uid, status: upsert_calls.append(
            {"course_id": cid, "student_id": uid, "status": status}
        ),
    )
    return upsert_calls


# ----------------------------------------------------------------------
# TC-US12-01 — normal case
# ----------------------------------------------------------------------

def test_tc_us12_01_admin_enrolls_valid_student(monkeypatch):
    """
    TC-US12-01 · US12 · normal

    Admin enrolls an Active Student who has no prior enrollment in the
    course. Expect `upsert_enrollment` to be called exactly once with
    status="Active" for the right (course_id, student_id).
    """
    _patch_admin_auth(monkeypatch)
    upsert_calls = _patch_course_and_user(
        monkeypatch,
        user_row=mock_data_us12.ACTIVE_STUDENT_ROW,
        existing_status=mock_data_us12.ENROLLMENT_NONE,
    )

    add_enrollment("admin@univ.edu", mock_data_us12.COURSE_ID, "minhhd@univ.edu")

    assert len(upsert_calls) == 1
    call = upsert_calls[0]
    assert call["course_id"] == mock_data_us12.COURSE_ID
    assert call["student_id"] == 4         # ACTIVE_STUDENT_ROW user_id
    assert call["status"] == "Active"


# ----------------------------------------------------------------------
# TC-US12-02 — error case
# ----------------------------------------------------------------------

def test_tc_us12_02_cannot_enroll_non_student(monkeypatch):
    """
    TC-US12-02 · US12 · error

    The admin tries to enroll `lanpt@univ.edu`, a Lecturer. The service
    must refuse with 422 BEFORE any enrollment row is written.
    """
    _patch_admin_auth(monkeypatch)
    upsert_calls = _patch_course_and_user(
        monkeypatch,
        user_row=mock_data_us12.LECTURER_ROW,
        existing_status=mock_data_us12.ENROLLMENT_NONE,  # never reached
    )

    with pytest.raises(ValidationError) as exc_info:
        add_enrollment("admin@univ.edu", mock_data_us12.COURSE_ID, "lanpt@univ.edu")

    assert "not a Student" in exc_info.value.message
    assert "Lecturer" in exc_info.value.message
    assert exc_info.value.status_code == 422
    # Nothing was written:
    assert upsert_calls == []


# ----------------------------------------------------------------------
# TC-US12-03 — boundary on both sides of two rules
# ----------------------------------------------------------------------

@pytest.mark.parametrize(
    "user_row, existing_status, expected_kind",
    [
        # Enrollment-state boundary (0 → new enrollment is allowed)
        pytest.param(
            mock_data_us12.ACTIVE_STUDENT_ROW,
            mock_data_us12.ENROLLMENT_NONE,
            "success",
            id="TC-US12-03a-never-enrolled",
        ),
        # Enrollment-state boundary (already Active → conflict)
        pytest.param(
            mock_data_us12.ACTIVE_STUDENT_ROW,
            mock_data_us12.ENROLLMENT_ACTIVE,
            "conflict",
            id="TC-US12-03b-already-active",
        ),
        # Enrollment-state boundary (previously Removed → can be restored)
        pytest.param(
            mock_data_us12.ACTIVE_STUDENT_ROW,
            mock_data_us12.ENROLLMENT_REMOVED,
            "success",
            id="TC-US12-03c-previously-removed",
        ),
        # Account-status boundary (Disabled → refused before enrollment)
        pytest.param(
            mock_data_us12.DISABLED_STUDENT_ROW,
            mock_data_us12.ENROLLMENT_NONE,
            "disabled",
            id="TC-US12-03d-disabled-account",
        ),
    ],
)
def test_tc_us12_03_enrollment_boundaries(
    monkeypatch, user_row, existing_status, expected_kind,
):
    """
    TC-US12-03 · US12 · boundary (both sides of two rules)

    Two rules are checked with parametrized cases:

      * ENROLLMENT-STATE (3-way boundary)
          not enrolled yet  → succeeds, new row inserted as "Active"
          already "Active"  → 409 conflict, no write
          previously "Removed" → succeeds, row restored to "Active"

      * ACCOUNT-STATUS (2-way boundary)
          Active Student    → accepted
          Disabled Student  → 422 refused, no write

    Together these cover both sides of each boundary the service checks.
    """
    _patch_admin_auth(monkeypatch)
    upsert_calls = _patch_course_and_user(
        monkeypatch,
        user_row=user_row,
        existing_status=existing_status,
    )

    if expected_kind == "success":
        add_enrollment("admin@univ.edu", mock_data_us12.COURSE_ID, "minhhd@univ.edu")
        assert len(upsert_calls) == 1
        assert upsert_calls[0]["status"] == "Active"
    elif expected_kind == "conflict":
        with pytest.raises(ConflictError) as exc_info:
            add_enrollment("admin@univ.edu", mock_data_us12.COURSE_ID, "minhhd@univ.edu")
        assert "already enrolled" in exc_info.value.message
        assert exc_info.value.status_code == 409
        assert upsert_calls == []
    else:  # "disabled"
        with pytest.raises(ValidationError) as exc_info:
            add_enrollment("admin@univ.edu", mock_data_us12.COURSE_ID, "minhhd@univ.edu")
        assert "disabled" in exc_info.value.message.lower()
        assert exc_info.value.status_code == 422
        assert upsert_calls == []