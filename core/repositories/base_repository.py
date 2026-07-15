"""Base repository with shared database query helpers."""

from typing import Any, Optional, Sequence

from database.db_manager import get_connection, adapt_sql


class BaseSqliteRepository:
    """
    Shared query helpers for database-backed repositories.
    Works with both SQLite (local) and PostgreSQL (cloud/Supabase).
    """

    def _fetch_all(self, query: str, params: Sequence[Any] = ()) -> list:
        query = adapt_sql(query)
        connection = get_connection()
        try:
            cur = connection.cursor()
            cur.execute(query, params)
            rows = cur.fetchall()
            return [dict(r) for r in rows]
        finally:
            connection.close()

    def _fetch_one(self, query: str, params: Sequence[Any] = ()) -> Optional[dict]:
        query = adapt_sql(query)
        connection = get_connection()
        try:
            cur = connection.cursor()
            cur.execute(query, params)
            row = cur.fetchone()
            return dict(row) if row else None
        finally:
            connection.close()

    def _execute(self, query: str, params: Sequence[Any] = ()) -> int:
        """Run a single write statement. Returns lastrowid / RETURNING id."""
        from database.db_manager import _BACKEND
        connection = get_connection()
        try:
            if _BACKEND == "postgres":
                # Append RETURNING for tables that need an id back
                # Repositories that need the id should use execute_returning_id directly
                cur = connection.cursor()
                cur.execute(adapt_sql(query), params)
                connection.commit()
                # Try to get RETURNING value if present
                try:
                    row = cur.fetchone()
                    if row:
                        return list(dict(row).values())[0]
                except Exception:
                    pass
                return 0
            else:
                cursor = connection.execute(query, params)
                connection.commit()
                return cursor.lastrowid
        finally:
            connection.close()
