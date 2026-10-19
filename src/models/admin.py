"""
admin.py — request/response shapes for admin endpoints (US06, US11, US12).

Only safe fields are exposed: `password` / `password_hash` never appear
in any response. The single-user GET returns the same `UserAdminResponse`
shape as the list endpoint.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


Role = Literal["Student", "Lecturer", "Admin"]
Status = Literal["Active", "Disabled"]


# ----------------------------------------------------------------------
# Users
# ----------------------------------------------------------------------

class UserCreateRequest(BaseModel):
    email: str = Field(..., description="Unique email address")
    full_name: str = Field(..., min_length=1, max_length=255)
    password: str = Field(..., min_length=1, description="Initial password (plain; hashed server-side)")
    role: Role
    status: Status = "Active"


class UserUpdateRequest(BaseModel):
    email: str | None = None
    full_name: str | None = None
    password: str | None = Field(
        default=None,
        description="If set, resets the password. If null/empty, keeps the current one.",
    )
    role: Role | None = None
    status: Status | None = None


class UserAdminResponse(BaseModel):
    """Safe shape used for list / get / create / update responses."""
    user_id: int
    email: str
    full_name: str
    role: str
    status: str
    created_at: datetime


class UserAdminListResponse(BaseModel):
    count: int
    users: list[UserAdminResponse]


class UserDeleteResponse(BaseModel):
    deleted: bool
    user_id: int


# ----------------------------------------------------------------------
# Courses (read-only roster view for US06's "per course" listing)
# ----------------------------------------------------------------------

class AdminCourseResponse(BaseModel):
    course_id: int
    code: str
    name: str
    lecturer_id: int
    lecturer_name: str | None = None
    lecturer_email: str | None = None
    student_count: int = 0


class AdminCourseListResponse(BaseModel):
    count: int
    courses: list[AdminCourseResponse]


class CourseRosterEntry(BaseModel):
    user_id: int
    email: str
    full_name: str
    status: str                    # enrollment status: Active / Removed
    enrolled_at: datetime
    role: str = Field(                # NEW — user's global role
        ..., description="User's global role: Student | Lecturer | Admin"
    )


class CourseRosterResponse(BaseModel):
    course_id: int
    code: str
    name: str
    lecturer: UserAdminResponse | None = None
    students: list[CourseRosterEntry]