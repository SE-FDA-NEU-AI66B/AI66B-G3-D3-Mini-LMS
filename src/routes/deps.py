"""
deps.py — shared FastAPI dependencies.

`current_email` prefers the signed session cookie (set by the SSO
callback) and falls back to the `email` query parameter for backwards
compatibility with the pre-auth walking-skeleton demo URLs.
"""

from __future__ import annotations

from fastapi import HTTPException, Query, Request


def current_email(
    request: Request,
    email: str | None = Query(
        None,
        description=(
            "Fallback email for pre-auth demo URLs. Ignored when a "
            "session cookie is present."
        ),
        examples=["lanpt@univ.edu"],
    ),
) -> str:
    # 1) Session cookie (SSO) wins.
    token = request.cookies.get("minilms_session")
    if token:
        from src.services.auth_service import read_session_token
        user = read_session_token(token)
        if user and user.get("email"):
            return user["email"]

    # 2) Fallback to ?email= for demo / debug URLs.
    if email and "@" in email:
        return email

    raise HTTPException(status_code=401, detail="Not authenticated")