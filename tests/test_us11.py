"""
Automated tests for US11 — Admin creates a course and assigns a lecturer.

Three test cases:

  TC-US11-01  normal    — the admin creates a course with a valid
                          Lecturer; the code is normalized to uppercase
                          and the course is persisted with the
                          expected fields
  TC-US11-02  error     — creating a course whose code already exists
                          is refused with a 409; the INSERT never runs
  TC-US11-03  boundary  — both sides of the numeric boundary
                          `lecturer_id > 0`, and both sides of the
                          role check "assigned user must be a Lecturer"

Every test runs WITHOUT a real database and WITHOUT a running server:
`db_config.connect` and the repository layer inside admin_service are
monkeypatched with canned values from mock_data_us11.py.

Run from the repository root:

    python -m pytest test/test_us11.py -v
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
from pydantic import ValidationError as PydanticValidationError

from src.models.admin import CourseCreateRequest
from src.services.admin_service import (
    create_course,
    ConflictError,
    ValidationError as ServiceValidationError,
)

import mock_data_us11


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
        lambda conn, email: mock_data_us11.ADMIN_AUTH_ROW,
    )


# ----------------------------------------------------------------------
# TC-US11-01 — normal case
# ----------------------------------------------------------------------

def test_tc_us11_01_admin_creates_course(monkeypatch):
    """
    TC-US11-01 · US11 · normal

    Admin creates a course with:
      * code "math201" — lowercase on purpose; the service must
        normalize it to "MATH201" before any DB write
      * name "Discrete Mathematics"
      * lecturer_id 2 — a valid Lecturer

    Expect: AdminCourseResponse with the normalized code and the
    lecturer's name/email; `insert_course` was called exactly once,
    with the uppercased code and the correct lecturer_id.
    """
    _patch_admin_auth(monkeypatch)

    # No conflicting course in the DB.
    monkeypatch.setattr(
        "src.services.admin_service.repo.get_course_by_code",
        lambda conn, code: None,
    )

    # The assigned user is a valid Lecturer.
    monkeypatch.setattr(
        "src.services.admin_service.repo.get_user",
        lambda conn, uid: mock_data_us11.VALID_LECTURER_ROW,
    )

    # Capture what `insert_course` receives.
    insert_calls = []

    def fake_insert_course(conn, code, name, lecturer_id):
        insert_calls.append({"code": code, "name": name, "lecturer_id": lecturer_id})
        return 4

    monkeypatch.setattr(
        "src.services.admin_service.repo.insert_course",
        fake_insert_course,
    )

    # The row that `get_course_admin(4)` will fetch after the insert.
    monkeypatch.setattr(
        "src.services.admin_service.repo.get_course_admin",
        lambda conn, cid: mock_data_us11.course_row(
            course_id=4,
            code="MATH201",
            name="Discrete Mathematics",
            lecturer_id=2,
        ),
    )

    payload = CourseCreateRequest(
        code="math201",             # lowercase — service must normalize
        name="Discrete Mathematics",
        lecturer_id=2,
    )
    result = create_course("admin@univ.edu", payload)

    # Response shape
    assert result.course_id == 4
    assert result.code == "MATH201"           # normalized to uppercase
    assert result.name == "Discrete Mathematics"
    assert result.lecturer_id == 2
    assert result.lecturer_name == "Pham Thi Lan"
    assert result.lecturer_email == "lanpt@univ.edu"
    assert result.student_count == 0

    # Insert happened exactly once, with the normalized code.
    assert len(insert_calls) == 1
    assert insert_calls[0]["code"] == "MATH201"       # uppercase, not "math201"
    assert insert_calls[0]["name"] == "Discrete Mathematics"
    assert insert_calls[0]["lecturer_id"] == 2


# ----------------------------------------------------------------------
# TC-US11-02 — error case
# ----------------------------------------------------------------------

def test_tc_us11_02_duplicate_course_code_refused(monkeypatch):
    """
    TC-US11-02 · US11 · error

    The admin tries to create a course whose code already exists.
    The service must raise ConflictError(409) BEFORE any INSERT runs.
    """
    _patch_admin_auth(monkeypatch)

    # A course with this code already exists in the DB.
    monkeypatch.setattr(
        "src.services.admin_service.repo.get_course_by_code",
        lambda conn, code: mock_data_us11.EXISTING_COURSE_CODE_ROW,
    )

    insert_calls = []
    monkeypatch.setattr(
        "src.services.admin_service.repo.insert_course",
        lambda *args, **kwargs: insert_calls.append(args) or 999,
    )

    payload = CourseCreateRequest(
        code="ACC101",                # duplicate
        name="Introduction to Accounting",
        lecturer_id=2,
    )

    with pytest.raises(ConflictError) as exc_info:
        create_course("admin@univ.edu", payload)

    assert "already exists" in exc_info.value.message
    assert "ACC101" in exc_info.value.message
    assert exc_info.value.status_code == 409
    # Nothing was inserted:
    assert insert_calls == []


# ----------------------------------------------------------------------
# TC-US11-03 — boundary on both sides of two rules
# ----------------------------------------------------------------------

@pytest.mark.parametrize(
    "lecturer_id, lecturer_row_for_mock, expected_kind",
    [
        # Below the numeric boundary (>0): Pydantic rejects at model level
        pytest.param(0,   None,                          "pydantic_reject",
                     id="TC-US11-03a-below-zero"),
        # At the numeric boundary: valid Lecturer succeeds
        pytest.param(1,   mock_data_us11.VALID_LECTURER_ROW, "success",
                     id="TC-US11-03b-at-one-valid-lecturer"),
        # Well above the numeric boundary: valid Lecturer succeeds
        pytest.param(100, mock_data_us11.VALID_LECTURER_ROW, "success",
                     id="TC-US11-03c-far-above-valid-lecturer"),
        # At the numeric boundary but wrong role: service rejects
        pytest.param(1,   mock_data_us11.NON_LECTURER_ROW, "service_reject",
                     id="TC-US11-03d-at-one-wrong-role"),
    ],
)
def test_tc_us11_03_lecturer_id_boundaries(
    monkeypatch, lecturer_id, lecturer_row_for_mock, expected_kind,
):
    """
    TC-US11-03 · US11 · boundary (both sides of two rules)

    Two boundaries are checked:

      * NUMERIC — `lecturer_id > 0` (Pydantic, gt=0).
          0   → rejected by Pydantic at request construction
          1   → accepted (at the boundary)
          100 → accepted (well above the boundary)

      * ROLE — "the assigned user must be a valid Lecturer".
          valid Lecturer → succeeds
          Admin          → rejected by the service with 422
    """
    # --- Numeric boundary at the model level ---------------------
    if expected_kind == "pydantic_reject":
        with pytest.raises(PydanticValidationError):
            CourseCreateRequest(
                code="MATH201",
                name="Discrete Mathematics",
                lecturer_id=lecturer_id,
            )
        return

    # --- Above the numeric boundary: exercise the service --------
    _patch_admin_auth(monkeypatch)
    monkeypatch.setattr(
        "src.services.admin_service.repo.get_course_by_code",
        lambda conn, code: None,   # no duplicate
    )
    monkeypatch.setattr(
        "src.services.admin_service.repo.get_user",
        lambda conn, uid: lecturer_row_for_mock,
    )

    insert_calls = []
    monkeypatch.setattr(
        "src.services.admin_service.repo.insert_course",
        lambda conn, code, name, lid: insert_calls.append(
            {"code": code, "name": name, "lecturer_id": lid}
        ) or 4,
    )
    monkeypatch.setattr(
        "src.services.admin_service.repo.get_course_admin",
        lambda conn, cid: mock_data_us11.course_row(
            course_id=cid,
            code="MATH201",
            name="Discrete Mathematics",
            lecturer_id=lecturer_id,
        ),
    )

    payload = CourseCreateRequest(
        code="MATH201",
        name="Discrete Mathematics",
        lecturer_id=lecturer_id,
    )

    if expected_kind == "success":
        result = create_course("admin@univ.edu", payload)
        assert result.course_id == 4
        assert result.lecturer_id == lecturer_id
        assert len(insert_calls) == 1
    else:  # service_reject: wrong role
        with pytest.raises(ServiceValidationError) as exc_info:
            create_course("admin@univ.edu", payload)
        assert "valid Lecturer" in exc_info.value.message
        assert exc_info.value.status_code == 422
        # Nothing was inserted:
        assert insert_calls == []