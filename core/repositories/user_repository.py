"""
User repository.

Defines the contract AuthService depends on (UserRepositoryInterface) and
the SQLite-backed implementation. AuthService is written against the
interface only (dependency inversion) — this is why swapping the backing
store here required zero changes to auth_service.py, only which repository
class login.py instantiates.
"""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional

from core.repositories.base_repository import BaseSqliteRepository
from database.db_manager import get_connection

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class UserRecord:
    """Raw user data as stored — password_hash is never exposed outside the repository/service boundary."""

    user_id: int
    username: str
    password_hash: str
    salt: str
    full_name: str
    role: str
    shift_name: str


@dataclass(frozen=True)
class UserSummary:
    """Lightweight user info for admin listings — never includes password data."""

    user_id: int
    username: str
    full_name: str
    role: str
    shift_name: str
    is_active: bool


class UserRepositoryInterface(ABC):
    @abstractmethod
    def get_by_username(self, username: str) -> Optional[UserRecord]:
        """Return the matching user record, or None if no such username exists."""
        raise NotImplementedError

    @abstractmethod
    def list_all(self) -> list[UserSummary]:
        raise NotImplementedError

    @abstractmethod
    def get_by_id(self, user_id: int) -> Optional[UserSummary]:
        raise NotImplementedError

    @abstractmethod
    def create_user(
        self, username: str, password_hash: str, salt: str, full_name: str, role_id: int, shift_id: Optional[int]
    ) -> int:
        raise NotImplementedError

    @abstractmethod
    def get_role_id(self, role_name: str) -> Optional[int]:
        raise NotImplementedError

    @abstractmethod
    def update_user(self, user_id: int, full_name: str, role_id: int, shift_id: Optional[int]) -> None:
        raise NotImplementedError

    @abstractmethod
    def set_active(self, user_id: int, is_active: bool) -> None:
        raise NotImplementedError


class SqliteUserRepository(UserRepositoryInterface, BaseSqliteRepository):
    """SQLite-backed user repository, joining users to roles and shifts for display fields."""

    _SELECT_BY_USERNAME = """
        SELECT
            u.user_id,
            u.username,
            u.password_hash,
            u.salt,
            u.full_name,
            r.role_name AS role,
            s.shift_name,
            s.start_time,
            s.end_time
        FROM users u
        JOIN roles r ON r.role_id = u.role_id
        LEFT JOIN shifts s ON s.shift_id = u.shift_id
        WHERE u.username = ? AND u.is_active = 1
    """

    def get_by_username(self, username: str) -> Optional[UserRecord]:
        connection = get_connection()
        try:
            row = connection.execute(self._SELECT_BY_USERNAME, (username,)).fetchone()
        finally:
            connection.close()

        if row is None:
            return None

        shift_display = (
            f"{row['shift_name']} · {row['start_time']}-{row['end_time']}"
            if row["shift_name"]
            else "Unassigned"
        )

        return UserRecord(
            user_id=row["user_id"],
            username=row["username"],
            password_hash=row["password_hash"],
            salt=row["salt"],
            full_name=row["full_name"],
            role=row["role"],
            shift_name=shift_display,
        )

    def list_all(self) -> list[UserSummary]:
        rows = self._fetch_all(
            """
            SELECT u.user_id, u.username, u.full_name, r.role_name AS role,
                   s.shift_name, u.is_active
            FROM users u
            JOIN roles r ON r.role_id = u.role_id
            LEFT JOIN shifts s ON s.shift_id = u.shift_id
            ORDER BY u.username
            """
        )
        return [
            UserSummary(
                user_id=row["user_id"],
                username=row["username"],
                full_name=row["full_name"],
                role=row["role"],
                shift_name=row["shift_name"] or "Unassigned",
                is_active=bool(row["is_active"]),
            )
            for row in rows
        ]

    def get_by_id(self, user_id: int) -> Optional[UserSummary]:
        row = self._fetch_one(
            """
            SELECT u.user_id, u.username, u.full_name, r.role_name AS role,
                   s.shift_name, u.is_active
            FROM users u
            JOIN roles r ON r.role_id = u.role_id
            LEFT JOIN shifts s ON s.shift_id = u.shift_id
            WHERE u.user_id = ?
            """,
            (user_id,),
        )
        if row is None:
            return None
        return UserSummary(
            user_id=row["user_id"],
            username=row["username"],
            full_name=row["full_name"],
            role=row["role"],
            shift_name=row["shift_name"] or "Unassigned",
            is_active=bool(row["is_active"]),
        )

    def create_user(
        self, username: str, password_hash: str, salt: str, full_name: str, role_id: int, shift_id: Optional[int]
    ) -> int:
        return self._execute(
            """
            INSERT INTO users (username, password_hash, salt, full_name, role_id, shift_id)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (username, password_hash, salt, full_name, role_id, shift_id),
        )

    def get_role_id(self, role_name: str) -> Optional[int]:
        row = self._fetch_one("SELECT role_id FROM roles WHERE role_name = ?", (role_name,))
        return row["role_id"] if row else None

    def update_user(self, user_id: int, full_name: str, role_id: int, shift_id: Optional[int]) -> None:
        self._execute(
            "UPDATE users SET full_name = ?, role_id = ?, shift_id = ? WHERE user_id = ?",
            (full_name, role_id, shift_id, user_id),
        )

    def set_active(self, user_id: int, is_active: bool) -> None:
        self._execute("UPDATE users SET is_active = ? WHERE user_id = ?", (int(is_active), user_id))
