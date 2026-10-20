"""
admin_routes.py — HTTP layer for admin endpoints.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel

from src.models.admin import (
    AdminCourseListResponse,
    AdminCourseResponse,
    CourseCreateRequest,
    CourseDeleteResponse,
    CourseRosterResponse,
    CourseUpdateRequest,
    UserAdminListResponse,
    UserAdminResponse,
    UserCreateRequest,
    UserDeleteResponse,
    UserUpdateRequest,
)
from src.routes.deps import current_email
from src.services import admin_service

router = APIRouter(prefix="/api/admin", tags=["admin"])


class EnrollmentRequest(BaseModel):
    student_email: str


# ------------------------------- users --------------------------------

@router.get("/accounts", response_model=UserAdminListResponse, summary="List user accounts (US06)")
def list_accounts(role: str | None = Query(None), status: str | None = Query(None), q: str | None = Query(None), user_id: int | None = Query(None), email: str = Depends(current_email)) -> UserAdminListResponse:
    return admin_service.list_users(email, role=role, status=status, q=q, user_id=user_id)


@router.post("/accounts", response_model=UserAdminResponse, status_code=status.HTTP_201_CREATED, summary="Create user (US06)")
def create_account(payload: UserCreateRequest, email: str = Depends(current_email)) -> UserAdminResponse:
    return admin_service.create_user(email, payload)


@router.get("/accounts/{user_id}", response_model=UserAdminResponse, summary="Get user")
def get_account(user_id: int, email: str = Depends(current_email)) -> UserAdminResponse:
    return admin_service.get_user(email, user_id)


@router.patch("/accounts/{user_id}", response_model=UserAdminResponse, summary="Update user (US06)")
def update_account(user_id: int, payload: UserUpdateRequest, email: str = Depends(current_email)) -> UserAdminResponse:
    return admin_service.update_user(email, user_id, payload)


@router.delete("/accounts/{user_id}", response_model=UserDeleteResponse, summary="Delete user (US06)")
def delete_account(user_id: int, email: str = Depends(current_email)) -> UserDeleteResponse:
    admin_service.delete_user(email, user_id)
    return UserDeleteResponse(deleted=True, user_id=user_id)


# ------------------------------ courses -------------------------------

@router.get("/courses", response_model=AdminCourseListResponse, summary="List all courses")
def list_courses(email: str = Depends(current_email)) -> AdminCourseListResponse:
    return admin_service.list_courses(email)


@router.post("/courses", response_model=AdminCourseResponse, status_code=status.HTTP_201_CREATED, summary="Create a course (US11)")
def create_course(payload: CourseCreateRequest, email: str = Depends(current_email)) -> AdminCourseResponse:
    return admin_service.create_course(email, payload)


@router.put("/courses/{course_id}", response_model=AdminCourseResponse, summary="Update a course (US11)")
def update_course(course_id: int, payload: CourseUpdateRequest, email: str = Depends(current_email)) -> AdminCourseResponse:
    return admin_service.update_course(email, course_id, payload)


@router.delete("/courses/{course_id}", response_model=CourseDeleteResponse, summary="Delete a course (US11)")
def delete_course(course_id: int, email: str = Depends(current_email)) -> CourseDeleteResponse:
    admin_service.delete_course(email, course_id)
    return CourseDeleteResponse(deleted=True, course_id=course_id)


@router.get("/courses/{course_id}/roster", response_model=CourseRosterResponse, summary="Get roster")
def get_roster(course_id: int, email: str = Depends(current_email)) -> CourseRosterResponse:
    return admin_service.get_course_roster(email, course_id)


# ---------------------------- enrollments -----------------------------

@router.post("/courses/{course_id}/enrollments", status_code=status.HTTP_201_CREATED, summary="Enroll student (US12)")
def add_enrollment(course_id: int, payload: EnrollmentRequest, email: str = Depends(current_email)):
    admin_service.add_enrollment(email, course_id, payload.student_email)
    return {"ok": True, "message": "Student enrolled successfully"}


@router.delete("/courses/{course_id}/enrollments/{student_id}", status_code=status.HTTP_200_OK, summary="Remove student (US12)")
def remove_enrollment(course_id: int, student_id: int, email: str = Depends(current_email)):
    admin_service.remove_enrollment(email, course_id, student_id)
    return {"ok": True, "message": "Student removed successfully"}