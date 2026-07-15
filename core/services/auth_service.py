"""
Authentication service.

Scope is deliberately minimal: salted-hash password verification and a
role string on the returned User. No JWT, no token refresh, no RBAC
engine — those belong in a real identity system, not a manufacturing
prototype's internship-scope auth. See Phase 2 architecture notes for
the reasoning.
"""

import hashlib
import hmac
from dataclasses import dataclass
from typing import Optional

from core.repositories.user_repository import UserRepositoryInterface


@dataclass(frozen=True)
class User:
    """Authenticated user, safe to store in session state (no password data)."""

    user_id: int
    username: str
    full_name: str
    role: str
    shift_name: str

    @property
    def is_admin(self) -> bool:
        return self.role == "admin"


class AuthService:
    """Verifies credentials against a UserRepositoryInterface and returns a User on success."""

    def __init__(self, user_repository: UserRepositoryInterface) -> None:
        self._user_repository = user_repository

    def authenticate(self, username: str, password: str) -> Optional[User]:
        """
        Verify a username/password pair.

        Returns:
            A User on success, or None if the username doesn't exist or
            the password doesn't match. Deliberately doesn't distinguish
            the two failure cases in its return value — the login page
            shows one generic error either way, so it can't be used to
            enumerate valid usernames.
        """
        record = self._user_repository.get_by_username(username)
        if record is None:
            return None

        if not self._verify_password(password, record.salt, record.password_hash):
            return None

        return User(
            user_id=record.user_id,
            username=record.username,
            full_name=record.full_name,
            role=record.role,
            shift_name=record.shift_name,
        )

    @staticmethod
    def hash_password(password: str, salt: str) -> str:
        """
        PBKDF2-HMAC-SHA256 password hash, 100k iterations.

        Standard-library only (no bcrypt dependency) — sufficient for a
        prototype's threat model, documented here so the choice reads as
        deliberate rather than an oversight in a viva.
        """
        derived = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 100_000)
        return derived.hex()

    @classmethod
    def _verify_password(cls, password: str, salt: str, expected_hash: str) -> bool:
        candidate_hash = cls.hash_password(password, salt)
        return hmac.compare_digest(candidate_hash, expected_hash)
