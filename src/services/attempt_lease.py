"""
attempt_lease.py — in-memory lease store for "one device at a time".

Each attempt can be held by at most one device_id at any moment. A device
holds the lease by refreshing it (heartbeat / save / submit) at least once
per LEASE_TTL_SECONDS. When the TTL expires, another device may claim it
without an explicit takeover — this covers the "browser crashed" case.

Deliberately in-memory: a server restart wipes all leases, which is fine
— attempts are still persisted in the DB, and the first post-restart
request re-acquires the lease for the current device. Avoids touching the
frozen schema, and avoids writing every heartbeat to PostgreSQL.

Thread-safety: single process, dict + threading.Lock.
"""

from __future__ import annotations

import threading
import time

LEASE_TTL_SECONDS = 30


class AttemptLeaseManager:
    def __init__(self, ttl: int = LEASE_TTL_SECONDS) -> None:
        self._ttl = ttl
        self._lock = threading.Lock()
        # attempt_id -> (device_id, last_seen_monotonic)
        self._leases: dict[int, tuple[str, float]] = {}

    def acquire(
        self, attempt_id: int, device_id: str, force: bool = False
    ) -> tuple[bool, str | None]:
        """
        Try to acquire or refresh the lease for attempt_id.

        Returns (ok, current_owner).
          - ok=True  → this device now holds the lease.
          - ok=False → current_owner is the device that holds it.
        """
        if not device_id:
            return False, None

        now = time.monotonic()
        with self._lock:
            entry = self._leases.get(attempt_id)
            if entry is None:
                self._leases[attempt_id] = (device_id, now)
                return True, device_id

            current_owner, last_seen = entry
            stale = (now - last_seen) > self._ttl

            if current_owner == device_id or force or stale:
                self._leases[attempt_id] = (device_id, now)
                return True, device_id

            return False, current_owner

    def release(self, attempt_id: int, device_id: str) -> bool:
        """Release the lease if this device currently owns it."""
        with self._lock:
            entry = self._leases.get(attempt_id)
            if entry is None:
                return False
            current_owner, _ = entry
            if current_owner != device_id:
                return False
            del self._leases[attempt_id]
            return True

    def force_release(self, attempt_id: int) -> None:
        """Release regardless of owner (used when the attempt is finalized)."""
        with self._lock:
            self._leases.pop(attempt_id, None)

    def owner(self, attempt_id: int) -> str | None:
        with self._lock:
            entry = self._leases.get(attempt_id)
            return entry[0] if entry else None

    def clear(self) -> None:
        with self._lock:
            self._leases.clear()


# Single global instance — one process, one module.
lease_manager = AttemptLeaseManager()