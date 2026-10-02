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
from fastapi import FastAPI

from src.config import settings
from src.routes import health_routes, quiz_routes


app = FastAPI(
    title="Mini-LMS API",
    version="0.1.0",
    description=(
        "Quiz platform for a single course workflow. "
        "See docs/design.md for the full architecture and API table."
    ),
)

app.include_router(health_routes.router)
app.include_router(quiz_routes.router)


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
    print("  http://localhost:8000/")
    print("  http://127.0.0.1:8000/")
    print("  http://localhost:8000/api/quizzes?email=minhhd@univ.edu")
    print("  API docs: http://localhost:8000/docs")
    print()

    uvicorn.run(
        "src.app:app",
        host="0.0.0.0",          # bind on every interface (needed for LAN / marker)
        port=8000,
        reload=True,
        log_level="info",
    )