"""
auth_routes.py — SSO mock + login/logout + /api/me.

Flow:
  GET  /login                  serves login.html (SP landing)
  GET  /mock-sso/authorize     serves mock-sso.html (mock IdP form)
  POST /mock-sso/authorize     verifies credentials, returns {redirect:…}
  GET  /auth/callback?code=…   verifies code, sets session cookie, redirects
  GET  /api/me                 returns current user from cookie
  POST /api/auth/logout        clears session cookie

No SQL and no business rules here — the service does all of that.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from pydantic import BaseModel, Field

from src.services import auth_service


router = APIRouter(tags=["auth"])


class LoginRequest(BaseModel):
    email: str = Field(..., description="User email")
    password: str = Field(..., description="Plain password")


# ------------------------------- pages --------------------------------

@router.get("/login", include_in_schema=False)
def login_page() -> FileResponse:
    """Landing page with the 'Sign in with University SSO' button."""
    return FileResponse("src/ui/html/login.html")


@router.get("/mock-sso/authorize", include_in_schema=False)
def mock_sso_page() -> FileResponse:
    """Mock identity provider — email + password form."""
    return FileResponse("src/ui/html/mock-sso.html")


# --------------------------- mock SSO submit --------------------------

@router.post(
    "/mock-sso/authorize",
    summary="Verify credentials and return a redirect to /auth/callback",
)
def mock_sso_authenticate(payload: LoginRequest):
    try:
        user = auth_service.authenticate(payload.email, payload.password)
    except auth_service.AuthError as exc:
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.message},
        )

    code = auth_service.issue_code(user)
    return {"redirect": f"/auth/callback?code={code}"}


# ---------------------------- SSO callback ----------------------------

@router.get("/auth/callback", include_in_schema=False)
def auth_callback(code: str):
    try:
        user = auth_service.exchange_code(code)
    except auth_service.AuthError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message)

    token = auth_service.create_session_token(user)
    target = auth_service.role_home(user["role"])

    response = RedirectResponse(url=target, status_code=302)
    response.set_cookie(
        key=auth_service.SESSION_COOKIE,
        value=token,
        max_age=auth_service.SESSION_MAX_AGE,
        httponly=True,
        samesite="lax",
        path="/",
    )
    return response


# ------------------------------ me / out ------------------------------

@router.get("/api/me", summary="Return the signed-in user")
def me(request: Request):
    token = request.cookies.get(auth_service.SESSION_COOKIE)
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    user = auth_service.read_session_token(token)
    if user is None:
        raise HTTPException(status_code=401, detail="Not authenticated")

    active = auth_service.get_active_user_by_email(user["email"])
    if active is None:
        raise HTTPException(status_code=403, detail="Account is disabled")
    return active


@router.post("/api/auth/logout", summary="Clear the session cookie")
def logout():
    response = JSONResponse({"ok": True})
    response.delete_cookie(auth_service.SESSION_COOKIE, path="/")
    return response