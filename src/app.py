"""
app.py — the FastAPI application.

Assembles the routers and exposes the ASGI `app` object that uvicorn
serves. Nothing else lives here: no business rules, no SQL, no templates.

M5 additions to this file:

  * `GET /` now redirects to `/login`. That is what handles the
    "user removes the tail of the URL, only the domain is left" case —
    reaching https://…onrender.com (or …onrender.com/) lands on the
    sign-in screen. The JSON metadata that used to live at `/` is
    preserved at `/about` for quick deploy-time diagnostics.

  * A global exception handler for unhandled exceptions (typically
    `psycopg.OperationalError` when the database is unreachable, or a
    bug in a route that the service layer did not wrap). Browsers get
    a friendly `error.html`; API clients get JSON 5xx so `api.js` can
    still surface a message. If `error.html` is missing (first deploy),
    an inline fallback HTML page is served instead — the handler can
    never itself crash.

Run with:
    python src/app.py
    # or: uvicorn src.app:app --reload --port 8000
"""

from __future__ import annotations

import pathlib
import sys

# Allow running as `python src/app.py` from the repo root.
ROOT = pathlib.Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import psycopg
import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import (
    FileResponse,
    HTMLResponse,
    JSONResponse,
    RedirectResponse,
    Response,
)
from fastapi.staticfiles import StaticFiles

from src.config import settings
from src.routes import (
    admin_routes,
    attempt_routes,
    auth_routes,
    health_routes,
    instructor_quiz_routes,
    quiz_routes,
)
from src.services.admin_service import AdminServiceError
from src.services.attempt_service import AttemptServiceError
from src.services.instructor_quiz_service import InstructorServiceError

app = FastAPI(
    title="Mini-LMS API",
    version="1.0.0",
    description=(
        "Quiz platform for a single course workflow. "
        "See docs/design.md for the full architecture and API table."
    ),
)


# ---- No-cache for UI assets & HTML pages ----------------------------
@app.middleware("http")
async def _disable_cache_for_ui(request: Request, call_next):
    response = await call_next(request)
    path = request.url.path
    if path.startswith("/ui/") or path in ("/login", "/mock-sso/authorize"):
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
    return response


# ---- Central error translation for services ------------------------
@app.exception_handler(InstructorServiceError)
async def _instructor_error_handler(
    _request: Request, exc: InstructorServiceError
) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.message})


@app.exception_handler(AdminServiceError)
async def _admin_error_handler(
    _request: Request, exc: AdminServiceError
) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.message})


@app.exception_handler(AttemptServiceError)
async def _attempt_error_handler(
    _request: Request, exc: AttemptServiceError
) -> JSONResponse:
    content = {"detail": exc.message}
    if exc.extra:
        content.update(exc.extra)
    return JSONResponse(status_code=exc.status_code, content=content)


# ---- Friendly error screen for unhandled exceptions (M5) -----------
# Two handlers, both wired into the same response helpers:
#   * psycopg.Error   → 503 with a "service unavailable" message
#   * Exception       → 500 with a generic "something went wrong" message
# Browsers get an HTML page; API clients get JSON. The handler itself
# is written defensively — if the error page file is missing or
# unreadable, it falls back to an inline HTML string so a broken error
# handler cannot take down the whole app.

_ERROR_HTML_PATH = ROOT / "src" / "ui" / "html" / "error.html"


def _fallback_error_html() -> str:
    """Minimal self-contained error page — used when error.html is absent."""
    return (
        "<!doctype html><html lang='en'><head>"
        "<meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width,initial-scale=1'>"
        "<title>Mini-LMS \u00b7 Error</title>"
        "<link rel='stylesheet' href='/ui/css/mini-lms.css'>"
        "</head><body>"
        "<header class='topbar' role='banner'>"
        "<a class='topbar__brand' href='/'>"
        "<span class='topbar__mark'>L</span>Mini-LMS"
        "</a></header>"
        "<div class='app-shell'><div class='app-body'><main class='app-main'>"
        "<div class='app-container' style='max-width:560px'>"
        "<div class='card u-mt-6' style='text-align:center;padding:40px 20px'>"
        "<h1 class='page-title'>Something went wrong</h1>"
        "<p class='u-text-muted u-mt-4'>"
        "The service is temporarily unable to handle your request."
        "</p>"
        "<p class='u-text-muted u-text-sm'>"
        "If this keeps happening, contact the administrator."
        "</p>"
        "<p class='u-mt-6'>"
        "<a class='btn btn--primary' href='/login'>Back to login</a>"
        "</p>"
        "</div></div></main></div></div></body></html>"
    )


def _html_or_fallback(status_code: int) -> Response:
    """Serve the on-disk error page, or the inline fallback if it is missing."""
    try:
        if _ERROR_HTML_PATH.is_file():
            return FileResponse(
                _ERROR_HTML_PATH,
                status_code=status_code,
                media_type="text/html",
            )
    except Exception:  # noqa: BLE001 — never let the handler itself crash
        pass
    return HTMLResponse(status_code=status_code, content=_fallback_error_html())


@app.exception_handler(psycopg.Error)
async def _db_error_handler(request: Request, exc: psycopg.Error) -> Response:
    """
    Database-layer exceptions that reached the top of the stack.

    In practice this is a `psycopg.OperationalError` — the database is
    unreachable, restarting, or refusing connections. It is NOT a
    business-rule rejection (those are already translated by the
    services into 4xx responses).

    Browsers get a friendly HTML page with a 503; API clients get JSON.
    Uvicorn already logs the original traceback to stderr, so nothing
    is lost — the user-facing response is just made safe.
    """
    if request.url.path.startswith("/api/"):
        return JSONResponse(
            status_code=503,
            content={
                "detail": (
                    "The service is temporarily unable to reach the "
                    "database. Please try again in a moment."
                )
            },
        )
    return _html_or_fallback(503)


@app.exception_handler(Exception)
async def _generic_error_handler(request: Request, exc: Exception) -> Response:
    """
    Last-resort handler for anything else a route or middleware throws.

    API paths keep their JSON shape so `api.js` can still surface a
    message. Browser navigation gets the same error page, with a 500.
    Uvicorn logs the traceback to stderr; this handler only decides what
    the user sees.
    """
    if request.url.path.startswith("/api/"):
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error"},
        )
    return _html_or_fallback(500)


# ---- Static UI assets ------------------------------------------------
app.mount("/ui/css", StaticFiles(directory="src/ui/css"), name="ui-css")
app.mount("/ui/js", StaticFiles(directory="src/ui/js"), name="ui-js")
app.mount("/ui/html", StaticFiles(directory="src/ui/html", html=True), name="ui-html")

app.include_router(auth_routes.router)
app.include_router(health_routes.router)
app.include_router(quiz_routes.router)
app.include_router(instructor_quiz_routes.router)
app.include_router(admin_routes.router)
app.include_router(attempt_routes.router)


# ---- Root → login ----------------------------------------------------
# Handles every shape the deployed URL can arrive in:
#   https://<domain>            → 302 to /login
#   https://<domain>/           → 302 to /login
#   https://<domain>/?foo=bar   → 302 to /login
# Any deeper path (/ui/html/…, /api/…, /docs, /health) is unaffected.
@app.get("/", include_in_schema=False)
def root() -> RedirectResponse:
    return RedirectResponse(url="/login", status_code=302)


# ---- Service metadata (diagnostics) ---------------------------------
# The JSON that used to be at `/`. Moved here so the root URL always
# leads to the sign-in flow while a deploy can still be smoke-tested
# with `GET /about`.
@app.get("/about", include_in_schema=False)
def about() -> dict:
    return {
        "service": "Mini-LMS",
        "version": app.version,
        "docs": "/docs",
        "health": "/health",
        "login": "/login",
        "walking_skeleton": "/api/quizzes",
    }


if __name__ == "__main__":
    print()
    print("Mini-LMS is starting. Open one of these in your browser:")
    print("  http://localhost:8000/login")
    print("  http://localhost:8000/api/quizzes?email=minhhd@univ.edu")
    print("  Instructor CRUD: http://localhost:8000/api/instructor/quizzes?email=lanpt@univ.edu")
    print("  Admin CRUD: http://localhost:8000/api/admin/accounts?email=admin@univ.edu")
    print("  http://localhost:8000/docs")
    print()

    uvicorn.run(
        "src.app:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
    )