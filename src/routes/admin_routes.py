"""
admin_routes.py — HTTP layer for admin endpoints (US06).

No SQL, no business rules. All errors bubble as `AdminServiceError`
subclasses and are translated centrally in app.py.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query, status

from src.models.admin import (
    AdminCourseListResponse,
    CourseRosterResponse,
    UserAdminListResponse,
    UserAdminResponse,
    UserCreateRequest,
    UserDeleteResponse,
    UserUpdateRequest,
)
from src.routes.deps import current_email
from src.services import admin_service

router = APIRouter(prefix="/api/admin", tags=["admin"])


# ------------------------------- users --------------------------------

@router.get(
    "/accounts",
    response_model=UserAdminListResponse,
    summary="List user accounts with optional filters (US06)",
)
def list_accounts(
    role: str | None = Query(
        None, description="Filter by role: Student | Lecturer | Admin"
    ),
    status: str | None = Query(
        None, description="Filter by status: Active | Disabled"
    ),
    q: str | None = Query(
        None, description="Search by email or full name (case-insensitive)"
    ),
    user_id: int | None = Query(None, description="Filter by user id"),
    email: str = Depends(current_email),
) -> UserAdminListResponse:
    return admin_service.list_users(
        email, role=role, status=status, q=q, user_id=user_id
    )


@router.post(
    "/accounts",
    response_model=UserAdminResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new user account (US06)",
)
def create_account(
    payload: UserCreateRequest, email: str = Depends(current_email)
) -> UserAdminResponse:
    return admin_service.create_user(email, payload)


@router.get(
    "/accounts/{user_id}",
    response_model=UserAdminResponse,
    summary="Get a single user account",
)
def get_account(
    user_id: int, email: str = Depends(current_email)
) -> UserAdminResponse:
    return admin_service.get_user(email, user_id)


@router.patch(
    "/accounts/{user_id}",
    response_model=UserAdminResponse,
    summary="Update a user account (US06)",
)
def update_account(
    user_id: int,
    payload: UserUpdateRequest,
    email: str = Depends(current_email),
) -> UserAdminResponse:
    return admin_service.update_user(email, user_id, payload)


@router.delete(
    "/accounts/{user_id}",
    response_model=UserDeleteResponse,
    summary="Delete a user account (blocked if the user still owns data)",
)
def delete_account(
    user_id: int, email: str = Depends(current_email)
) -> UserDeleteResponse:
    admin_service.delete_user(email, user_id)
    return UserDeleteResponse(deleted=True, user_id=user_id)


# ------------------------------ courses -------------------------------

@router.get(
    "/courses",
    response_model=AdminCourseListResponse,
    summary="List all courses with their lecturer and student count",
)
def list_courses(email: str = Depends(current_email)) -> AdminCourseListResponse:
    return admin_service.list_courses(email)


@router.get(
    "/courses/{course_id}/roster",
    response_model=CourseRosterResponse,
    summary="Get a course's lecturer and enrolled students",
)
def get_roster(
    course_id: int, email: str = Depends(current_email)
) -> CourseRosterResponse:
    return admin_service.get_course_roster(email, course_id)