"""
health_routes.py — liveness and readiness probes.

Three endpoints, three purposes:

  GET /health/live   Process-only liveness. Always 200 while uvicorn is
                     running. Never touches the database, so a transient
                     DB blip cannot flap this probe.

  GET /health        Readiness. 200 only when the app AND the database
                     are both reachable. 503 when the database cannot
                     be reached. This is the endpoint M5's pass gate
                     names — "returns 200 when the app and the database
                     are fine, and 503 when not".

  GET /health/db     Same check as /health, kept under its original
                     path for backwards compatibility. Now returns 503
                     on failure (the old version returned 200 with an
                     error in the body).

The /health and /health/db handlers return JSONResponse directly so the
status code is honoured by FastAPI — raising HTTPException would work
too, but the response body would be reshaped by the framework. Returning
JSONResponse keeps the shape stable for uptime monitors that parse it.
"""

from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from src.config import db as db_config
from src.config import settings


router = APIRouter(tags=["health"])


# ----------------------------------------------------------------------
# Internal helpers
# ----------------------------------------------------------------------

def _check_db() -> tuple[bool, str | None]:
    """
    Open a short-lived connection and issue `SELECT 1`.

    Returns (ok, error_message):
      * (True, None)      — the database answered
      * (False, "<detail>") — the database is unreachable or erroring

    Kept defensive: any exception is caught and reported as a failure
    rather than propagated, because a health check that itself 500s is
    less useful than one that 503s cleanly.
    """
    try:
        with db_config.connect() as conn, conn.cursor() as cur:
            cur.execute("SELECT 1")
            cur.fetchone()
        return True, None
    except Exception as exc:  # noqa: BLE001 — surface any driver error as a failure
        return False, str(exc)


# ----------------------------------------------------------------------
# Liveness probe — process only
# ----------------------------------------------------------------------

@router.get(
    "/health/live",
    summary="Liveness probe — the process is running",
    description=(
        "Returns 200 whenever uvicorn is serving requests. Does not "
        "touch the database, so this probe is unaffected by a transient "
        "database outage. Suitable for a platform health check that "
        "restarts the container on repeated failure."
    ),
)
def health_live() -> dict:
    return {"status": "ok"}


# ----------------------------------------------------------------------
# Readiness probe — app + database
# ----------------------------------------------------------------------

@router.get(
    "/health",
    summary="Readiness probe — the app and the database are healthy",
    description=(
        "Returns 200 only when both the process and the database are "
        "reachable. Returns 503 when the database cannot be reached. "
        "This is the endpoint the M5 pass gate names."
    ),
)
def health() -> JSONResponse:
    ok, detail = _check_db()
    target = settings.describe_target()

    if ok:
        return JSONResponse(
            status_code=200,
            content={"status": "ok", "database": target},
        )

    return JSONResponse(
        status_code=503,
        content={
            "status": "error",
            "database": target,
            "detail": detail or "database unreachable",
        },
    )


# ----------------------------------------------------------------------
# Readiness probe — database-only (backwards-compatible path)
# ----------------------------------------------------------------------

@router.get(
    "/health/db",
    summary="Readiness probe (database only)",
    description=(
        "Same check as /health, kept under its original path for "
        "backwards compatibility. Now returns 503 (not 200) when the "
        "database cannot be reached."
    ),
)
def health_db() -> JSONResponse:
    ok, detail = _check_db()
    target = settings.describe_target()

    if ok:
        return JSONResponse(
            status_code=200,
            content={"status": "ok", "database": target},
        )

    return JSONResponse(
        status_code=503,
        content={
            "status": "error",
            "database": target,
            "detail": detail or "database unreachable",
        },
    )