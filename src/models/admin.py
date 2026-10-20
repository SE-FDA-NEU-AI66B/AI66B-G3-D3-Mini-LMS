"""
admin.py — request/response shapes for admin endpoints (US06, US11, US12).
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
# Courses (US11)
# ----------------------------------------------------------------------

class CourseCreateRequest(BaseModel):
    code: str = Field(..., min_length=1, max_length=20, description="Course code e.g. ACC101")
    name: str = Field(..., min_length=1, max_length=255)
    lecturer_id: int = Field(..., gt=0, description="ID of the assigned lecturer")


class CourseUpdateRequest(BaseModel):
    code: str | None = Field(default=None, min_length=1, max_length=20)
    name: str | None = Field(default=None, min_length=1, max_length=255)
    lecturer_id: int | None = Field(default=None, gt=0)


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


class CourseDeleteResponse(BaseModel):
    deleted: bool
    course_id: int


# ----------------------------------------------------------------------
# Roster & Enrollments
# ----------------------------------------------------------------------

class CourseRosterEntry(BaseModel):
    user_id: int
    email: str
    full_name: str
    status: str
    enrolled_at: datetime
    role: str


class CourseRosterResponse(BaseModel):
    course_id: int
    code: str
    name: str
    lecturer: UserAdminResponse | None = None
    students: list[CourseRosterEntry]