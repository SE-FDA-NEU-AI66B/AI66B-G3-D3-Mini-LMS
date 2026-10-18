"""
auth_service.py — mock SSO, credential verification, signed tokens.

Implements an OIDC-lite flow:
  * POST /mock-sso/authorize  →  verify email + password against
    "user".password (SHA-256 hex, see src/utils/password.py),
    return a short-lived signed "code".
  * GET  /auth/callback?code=…  →  exchange code for a session cookie,
    redirect to the role's home page.

The session cookie and the code share the same signed-token format:
    base64url(json_payload) "." hex(HMAC-SHA256(SESSION_SECRET, payload))

BR7's "never store passwords" clause is relaxed to "never store plaintext
passwords" — the column exists for the mock SSO only.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time

from src.config import db as db_config
from src.config import settings
from src.repositories import instructor_quiz_repository as repo
from src.utils.password import verify_password


SESSION_COOKIE = "minilms_session"
SESSION_MAX_AGE = 8 * 60 * 60   # 8 hours
CODE_MAX_AGE = 60               # 60 seconds


# ------------------------------- errors -------------------------------

class AuthError(Exception):
    def __init__(self, message: str, status_code: int = 401) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code


class InvalidCredentialsError(AuthError):
    def __init__(self) -> None:
        super().__init__("Invalid email or password", 401)


class DisabledAccountError(AuthError):
    def __init__(self) -> None:
        super().__init__("Account is disabled", 403)


class InvalidTokenError(AuthError):
    def __init__(self, message: str = "Invalid or expired token") -> None:
        super().__init__(message, 400)


# ----------------------------- signing --------------------------------

def _b64encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _b64decode(text: str) -> bytes:
    pad = "=" * (-len(text) % 4)
    return base64.urlsafe_b64decode(text + pad)


def _sign(payload: dict) -> str:
    body = _b64encode(
        json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    )
    secret = settings.SESSION_SECRET.encode("utf-8")
    sig = hmac.new(secret, body.encode("ascii"), hashlib.sha256).hexdigest()
    return f"{body}.{sig}"


def _unsign(token: str) -> dict:
    if not isinstance(token, str) or "." not in token:
        raise InvalidTokenError()
    body, sig = token.rsplit(".", 1)
    secret = settings.SESSION_SECRET.encode("utf-8")
    expected = hmac.new(secret, body.encode("ascii"), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(sig, expected):
        raise InvalidTokenError()
    try:
        payload = json.loads(_b64decode(body).decode("utf-8"))
    except Exception as exc:  # noqa: BLE001
        raise InvalidTokenError() from exc
    if not isinstance(payload, dict):
        raise InvalidTokenError()
    exp = payload.get("exp")
    if not isinstance(exp, (int, float)) or exp < time.time():
        raise InvalidTokenError("Token expired")
    return payload


# -------------------------- authentication ----------------------------

def authenticate(email: str, password: str) -> dict:
    """Verify credentials; return {user_id, email, full_name, role}."""
    if not email or "@" not in email:
        raise InvalidCredentialsError()
    if not password:
        raise InvalidCredentialsError()

    with db_config.connect() as conn:
        row = repo.get_user_full_by_email(conn, email)
    if row is None:
        raise InvalidCredentialsError()

    user_id, db_email, full_name, password_hash, role, status = row
    if not verify_password(password, password_hash):
        raise InvalidCredentialsError()
    if status != "Active":
        raise DisabledAccountError()

    return {
        "user_id": user_id,
        "email": db_email,
        "full_name": full_name,
        "role": role,
    }


# ---------------------------- code + session --------------------------

def issue_code(user: dict) -> str:
    """Short-lived identity code handed to /auth/callback."""
    return _sign({
        "sub": user["user_id"],
        "email": user["email"],
        "full_name": user["full_name"],
        "role": user["role"],
        "exp": int(time.time()) + CODE_MAX_AGE,
    })


def exchange_code(code: str) -> dict:
    payload = _unsign(code)
    return {
        "user_id": int(payload["sub"]),
        "email": payload["email"],
        "full_name": payload.get("full_name", ""),
        "role": payload["role"],
    }


def create_session_token(user: dict) -> str:
    return _sign({
        "sub": user["user_id"],
        "email": user["email"],
        "full_name": user.get("full_name", ""),
        "role": user["role"],
        "exp": int(time.time()) + SESSION_MAX_AGE,
    })


def read_session_token(token: str) -> dict | None:
    try:
        payload = _unsign(token)
    except AuthError:
        return None
    return {
        "user_id": int(payload["sub"]),
        "email": payload["email"],
        "full_name": payload.get("full_name", ""),
        "role": payload["role"],
    }


# ------------------------------ helpers -------------------------------

def get_active_user_by_email(email: str) -> dict | None:
    """Fresh read of a user row; returns None when missing or disabled."""
    with db_config.connect() as conn:
        row = repo.get_user_full_by_email(conn, email)
    if row is None:
        return None
    user_id, db_email, full_name, _pw, role, status = row
    if status != "Active":
        return None
    return {
        "user_id": user_id,
        "email": db_email,
        "full_name": full_name,
        "role": role,
    }


def role_home(role: str) -> str:
    """Where to send a user after successful login."""
    return {
        "Lecturer": "/ui/html/instructor-quizzes.html",
        "Student":  "/ui/html/student-dashboard.html",
        "Admin":    "/docs",
    }.get(role, "/login")