"""
deps.py — shared FastAPI dependencies.

Today, the caller's identity is taken from the `email` query parameter,
matching the walking-skeleton route (`GET /api/quizzes?email=...`). This
is temporary: BR7 delegates authentication to the university SSO. When
sessions land, only `current_email` changes — every router that depends
on it keeps working unchanged.
"""

from __future__ import annotations

from fastapi import HTTPException, Query


def current_email(
    email: str = Query(
        ...,
        description="Caller email. Temporary stand-in for the SSO session.",
        examples=["lanpt@univ.edu"],
    ),
) -> str:
    if not email or "@" not in email:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return email