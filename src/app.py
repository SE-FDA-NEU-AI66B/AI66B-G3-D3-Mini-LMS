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
from src.routes import health_routes, instructor_quiz_routes, quiz_routes
from src.services.instructor_quiz_service import InstructorServiceError

app = FastAPI(
    title="Mini-LMS API",
    version="0.1.0",
    description=(
        "Quiz platform for a single course workflow. "
        "See docs/design.md for the full architecture and API table."
    ),
)


# ---- Central error translation for the instructor service -----------
# Every `InstructorServiceError` subclass carries its own status_code and
# a human-readable message; the route layer never has to catch anything.
@app.exception_handler(InstructorServiceError)
async def _instructor_error_handler(
    _request: Request, exc: InstructorServiceError
) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.message})


# ---- Static UI assets ------------------------------------------------
app.mount("/ui/css", StaticFiles(directory="src/ui/css"), name="ui-css")
app.mount("/ui/js", StaticFiles(directory="src/ui/js"), name="ui-js")
app.mount("/ui/html", StaticFiles(directory="src/ui/html", html=True), name="ui-html")

app.include_router(health_routes.router)
app.include_router(quiz_routes.router)
app.include_router(instructor_quiz_routes.router)


@app.get("/", include_in_schema=False)
def root() -> dict:
    """A tiny landing response so hitting the root does not 404."""
    return {
        "service": "Mini-LMS",
        "docs": "/docs",
        "health": "/health",
        "walking_skeleton": "/api/quizzes",
    }


if __name__ == "__main__":
    # uvicorn prints "0.0.0.0:8000" because that is the bind address.
    # 0.0.0.0 is not a browsable host, so print the clickable URLs first.
    print()
    print("Mini-LMS is starting. Open one of these in your browser:")
    print("  http://localhost:8000/ui/html/demo.html")
    print("  http://localhost:8000/api/quizzes?email=minhhd@univ.edu")
    print("  Instructor CRUD: http://localhost:8000/api/instructor/quizzes?email=lanpt@univ.edu")
    print("  API docs: http://localhost:8000/docs")
    print()

    uvicorn.run(
        "src.app:app",
        host="0.0.0.0",          # bind on every interface (needed for LAN / marker)
        port=8000,
        reload=True,
        log_level="info",
    )