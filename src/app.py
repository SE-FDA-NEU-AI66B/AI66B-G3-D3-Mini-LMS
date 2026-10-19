"""
app.py — the FastAPI application.

Assembles the routers and exposes the ASGI `app` object that uvicorn
serves. Nothing else lives here: no business rules, no SQL, no templates.

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

import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from src.config import settings
from src.routes import (
    admin_routes,
    attempt_routes,                 # NEW
    auth_routes,
    health_routes,
    instructor_quiz_routes,
    quiz_routes,
)
from src.services.admin_service import AdminServiceError
from src.services.attempt_service import AttemptServiceError   # NEW
from src.services.instructor_quiz_service import InstructorServiceError

app = FastAPI(
    title="Mini-LMS API",
    version="0.1.0",
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


# ---- Central error translation --------------------------------------
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


@app.exception_handler(AttemptServiceError)     # NEW
async def _attempt_error_handler(
    _request: Request, exc: AttemptServiceError
) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.message})


# ---- Static UI assets ------------------------------------------------
app.mount("/ui/css", StaticFiles(directory="src/ui/css"), name="ui-css")
app.mount("/ui/js", StaticFiles(directory="src/ui/js"), name="ui-js")
app.mount("/ui/html", StaticFiles(directory="src/ui/html", html=True), name="ui-html")

app.include_router(auth_routes.router)
app.include_router(health_routes.router)
app.include_router(quiz_routes.router)
app.include_router(instructor_quiz_routes.router)
app.include_router(admin_routes.router)
app.include_router(attempt_routes.router)      # NEW


@app.get("/", include_in_schema=False)
def root() -> dict:
    return {
        "service": "Mini-LMS",
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