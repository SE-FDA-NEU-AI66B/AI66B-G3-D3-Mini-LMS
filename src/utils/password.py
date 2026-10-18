"""
password.py — SHA-256 password hashing helpers.

Kept dependency-free (stdlib only). This is deliberately a *plain*
SHA-256 (no salt, no stretching) because it matches the schema comment
and the seed hashes. If security requirements later demand salted/
stretched hashing (bcrypt / argon2 / PBKDF2), only this module changes —
callers keep using hash_password / verify_password.
"""

from __future__ import annotations

import hashlib
import hmac


def hash_password(plain: str) -> str:
    """Return the SHA-256 hex digest (64 chars) of the given plaintext."""
    return hashlib.sha256(plain.encode("utf-8")).hexdigest()


def verify_password(plain: str, hashed: str) -> bool:
    """Constant-time comparison of a plaintext against a stored SHA-256 digest."""
    if not isinstance(hashed, str):
        return False
    return hmac.compare_digest(hash_password(plain), hashed)