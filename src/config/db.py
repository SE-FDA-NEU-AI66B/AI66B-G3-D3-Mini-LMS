"""
db.py — the single place where a PostgreSQL connection is opened.

Every repository, script, and route goes through `connect()`. That way,
changing the database engine later means editing one file, not fifty.
"""

from __future__ import annotations

import psycopg

from . import settings


def connection_params(target_db: str | None = None) -> dict:
    return {
        "host": settings.DB_HOST,
        "port": settings.DB_PORT,
        "dbname": target_db or settings.DB_NAME,
        "user": settings.DB_USER,
        "password": settings.DB_PASSWORD,
    }


def connect(target_db: str | None = None, autocommit: bool = False) -> psycopg.Connection:
    """
    Open a connection to the Mini-LMS database.

    Pass target_db='postgres' to reach the maintenance database, which is
    what init_db.py uses when the target database does not exist yet.
    """
    return psycopg.connect(**connection_params(target_db), autocommit=autocommit)