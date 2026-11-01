"""
Automated tests for US02 — Student sees available quizzes.

Three test cases:

  TC-US02-01  normal     — an Active Student enrolled in two courses sees
                            both available and overdue quizzes, each with
                            the correct `availability` classification
  TC-US02-02  error      — a Lecturer (not a Student) is refused by the
                            role gate with a clear message        (BR8)
  TC-US02-03  error edge — a Disabled Student is refused with a distinct
                            message, exercising the Active/Disabled
                            status boundary                       (BR8)

Every test runs WITHOUT a real database and WITHOUT a running server:
the two repository functions inside quiz_service are monkeypatched with
canned values from mock_data_us02.py.

Run from the repository root:

    python -m pytest src/tests/test_us02_student_sees_quizzes.py -v
"""

from __future__ import annotations

import pathlib
import sys

# Make sure the repo root and this test directory are importable,
# regardless of how pytest is invoked (matches db/init_db.py's pattern).
ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

THIS_DIR = pathlib.Path(__file__).resolve().parent
if str(THIS_DIR) not in sys.path:
    sys.path.insert(0, str(THIS_DIR))

import pytest

from src.services.quiz_service import (
    list_visible_quizzes,
    StudentNotFoundError,
)

import mock_data_us02


# ----------------------------------------------------------------------
# Fakes — patch the two functions that would touch PostgreSQL
# ----------------------------------------------------------------------

def _patch_repo(monkeypatch, *, role_row, quizzes):
    """
    Replace the two repository functions that `list_visible_quizzes`
    consults. Neither mock opens a real connection, so the test never
    needs a live database.
    """
    monkeypatch.setattr(
        "src.services.quiz_service.quiz_repository.get_user_role_status",
        lambda email: role_row,
    )
    monkeypatch.setattr(
        "src.services.quiz_service.quiz_repository.find_visible_quizzes",
        lambda email: quizzes,
    )


# ----------------------------------------------------------------------
# TC-US02-01 — normal case
# ----------------------------------------------------------------------

def test_tc_us02_01_student_sees_available_and_overdue(monkeypatch):
    """
    TC-US02-01 · US02 · normal

    An Active Student enrolled in two courses sees four published quizzes:
    two with a future due date (`available`) and two already past due
    (`overdue`). The service must return all four, with the correct
    `availability` classification on each row.
    """
    _patch_repo(
        monkeypatch,
        role_row=mock_data_us02.ACTIVE_STUDENT_ROW,
        quizzes=mock_data_us02.MIXED_QUIZZES,
    )

    result = list_visible_quizzes("minhhd@univ.edu")

    # All four quizzes are visible — both buckets are preserved.
    assert len(result) == 4
    assert sum(1 for q in result if q.availability == "available") == 2
    assert sum(1 for q in result if q.availability == "overdue")   == 2

    # Titles and course codes pass through unchanged.
    titles = {q.title for q in result}
    assert "ACC101 Midterm Quiz"  in titles
    assert "ACC101 Overdue Quiz"  in titles

    codes = {q.course_code for q in result}
    assert codes == {"ACC101", "ACC201"}


# ----------------------------------------------------------------------
# TC-US02-02 — error case
# ----------------------------------------------------------------------

def test_tc_us02_02_lecturer_cannot_list_student_quizzes(monkeypatch):
    """
    TC-US02-02 · US02 · error

    A Lecturer is not a Student. Accessing the student-facing quiz list
    must be refused before the visibility query runs. The message must
    name the actual role so support can tell the two error cases apart.
    """
    _patch_repo(
        monkeypatch,
        role_row=mock_data_us02.ACTIVE_LECTURER_ROW,
        quizzes=[],   # intentionally empty — must never be reached
    )

    with pytest.raises(StudentNotFoundError) as exc_info:
        list_visible_quizzes("lanpt@univ.edu")

    message = str(exc_info.value)
    assert "not a student" in message
    assert "Lecturer" in message


# ----------------------------------------------------------------------
# TC-US02-03 — error edge case on the Active/Disabled status boundary
# ----------------------------------------------------------------------

def test_tc_us02_03_disabled_student_cannot_list_quizzes(monkeypatch):
    """
    TC-US02-03 · US02 · error (status boundary)

    BR8 says a disabled account cannot use the system. A Student whose
    status is `Disabled` must be refused with a message that clearly
    distinguishes "disabled" from "wrong role" — otherwise the support
    team can't tell the two cases apart. This is the boundary between
    the two user-status states (Active / Disabled).
    """
    _patch_repo(
        monkeypatch,
        role_row=mock_data_us02.DISABLED_STUDENT_ROW,
        quizzes=[],
    )

    with pytest.raises(StudentNotFoundError) as exc_info:
        list_visible_quizzes("minhhd@univ.edu")

    message = str(exc_info.value)
    assert "disabled" in message.lower()
    # The two error cases must remain distinguishable.
    assert "not a student" not in message