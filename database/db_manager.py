"""
Database connection management.

Supports two backends:
  - PostgreSQL (Supabase): when DATABASE_URL environment variable is set
  - SQLite (local dev):    when DATABASE_URL is not set

The public API is identical either way:
  get_connection()      -> connection object
  transaction()         -> context manager yielding a connection
  initialize_database() -> create tables and run seed
  adapt_sql(sql)        -> translate ? placeholders to %s for PostgreSQL

Repositories depend on this module; nothing above the repository layer
should import sqlite3 or psycopg2 directly.
"""

import logging
import os
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator, Any

logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv("DATABASE_URL")

# ── backend selection ─────────────────────────────────────────────────────────

if DATABASE_URL:
    import psycopg2
    import psycopg2.extras
    _BACKEND = "postgres"
else:
    import sqlite3 as _sqlite3
    _BACKEND = "sqlite"
    from config.settings import settings

logger.info("DB backend: %s", _BACKEND)


# ── placeholder adapter ──────────────────────────────────────────────────────

def adapt_sql(sql: str) -> str:
    """Translate SQLite ? placeholders to PostgreSQL %s when needed."""
    if _BACKEND == "postgres":
        return sql.replace("?", "%s")
    return sql


# ── connection helpers ────────────────────────────────────────────────────────

class _DictRow(dict):
    """dict subclass that also supports attribute-style access (row['key'] and row.key)."""
    def __getattr__(self, name):
        try:
            return self[name]
        except KeyError:
            raise AttributeError(name)



def _make_dict_connection_pg():
    """Open a psycopg2 connection whose cursors return _DictRow objects."""
    import urllib.parse
    parsed = urllib.parse.urlparse(DATABASE_URL)
    host = parsed.hostname or ""
    port = parsed.port or 5432
    dbname = (parsed.path or "/postgres").lstrip("/") or "postgres"
    user = parsed.username or ""
    password = urllib.parse.unquote(parsed.password or "")

    logger.info("Connecting to PostgreSQL: host=%s port=%s db=%s user=%s", host, port, dbname, user)

    # Try sslmode=prefer first (works with or without SSL enforcement),
    # then fall back to disable if that fails too.
    for sslmode in ("prefer", "disable", "require"):
        try:
            conn = psycopg2.connect(
                host=host,
                port=port,
                dbname=dbname,
                user=user,
                password=password,
                sslmode=sslmode,
                connect_timeout=20,
                cursor_factory=psycopg2.extras.RealDictCursor,
            )
            conn.autocommit = False
            logger.info("PostgreSQL connection established (sslmode=%s).", sslmode)
            return conn
        except psycopg2.OperationalError as e:
            err_msg = str(e).split("\n")[0]
            logger.warning("Connection attempt sslmode=%s failed: %s", sslmode, err_msg)
            last_err = e

    raise RuntimeError(
        f"Cannot connect to Supabase after trying all SSL modes.\n"
        f"Host: {host}  Port: {port}  DB: {dbname}  User: {user}\n"
        f"Last error type: {type(last_err).__name__}\n"
        f"Check DATABASE_URL secret in Streamlit Cloud settings."
    ) from last_err





def get_connection():
    """Open and return a new database connection."""
    if _BACKEND == "postgres":
        return _make_dict_connection_pg()
    else:
        connection = _sqlite3.connect(str(settings.paths.database_file))
        connection.execute("PRAGMA foreign_keys = ON")
        connection.row_factory = _sqlite3.Row
        return connection


@contextmanager
def transaction() -> Iterator:
    """
    Context manager for a single atomic transaction.
    Commits on clean exit, rolls back on any exception, always closes.
    """
    connection = get_connection()
    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        logger.exception("Transaction rolled back due to an error.")
        raise
    finally:
        connection.close()


# ── schema initialisation ─────────────────────────────────────────────────────

def initialize_database() -> None:
    """Create all tables if they don't exist. Safe to call on every startup."""
    if _BACKEND == "postgres":
        _initialize_postgres()
    else:
        _initialize_sqlite()


def _initialize_postgres() -> None:
    """Apply PostgreSQL schema."""
    schema_path = Path(__file__).resolve().parent / "schema_postgres.sql"
    schema_sql = schema_path.read_text(encoding="utf-8")
    with transaction() as conn:
        cur = conn.cursor()
        cur.execute(schema_sql)
    logger.info("PostgreSQL schema initialized (Supabase)")


def _initialize_sqlite() -> None:
    """Apply SQLite schema."""
    settings.paths.database_file.parent.mkdir(parents=True, exist_ok=True)
    schema_path = Path(__file__).resolve().parent / "schema.sql"
    schema_sql = schema_path.read_text(encoding="utf-8")
    with transaction() as conn:
        conn.executescript(schema_sql)
        _apply_sqlite_migrations(conn)
    logger.info("SQLite schema initialized at %s", settings.paths.database_file)


def _apply_sqlite_migrations(connection) -> None:
    """Additive migrations for SQLite (no-ops on fresh databases)."""
    try:
        connection.execute(
            "ALTER TABLE component_types ADD COLUMN is_active INTEGER NOT NULL DEFAULT 1"
        )
        logger.info("Migration applied: component_types.is_active")
    except _sqlite3.OperationalError:
        pass


def execute_returning_id(conn, sql: str, params: tuple) -> int:
    """
    Execute an INSERT and return the new row's primary key.
    Works for both SQLite (lastrowid) and PostgreSQL (RETURNING id).
    """
    if _BACKEND == "postgres":
        # SQL must end with RETURNING <pk_col>
        cur = conn.cursor()
        cur.execute(adapt_sql(sql), params)
        row = cur.fetchone()
        if row is None:
            raise RuntimeError("INSERT did not return an id")
        # RealDictCursor returns dict-like; grab first value
        return list(row.values())[0]
    else:
        cur = conn.execute(sql, params)
        return cur.lastrowid
