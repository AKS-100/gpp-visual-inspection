"""
Seed data for local development and demos.

Idempotent — uses INSERT OR IGNORE (SQLite) / INSERT ... ON CONFLICT DO NOTHING (PostgreSQL).
Password hashes are generated through AuthService.hash_password.
"""

import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from database.db_manager import initialize_database, transaction, _BACKEND
from core.services.auth_service import AuthService

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

# Use INSERT OR IGNORE for SQLite, INSERT ... ON CONFLICT DO NOTHING for PostgreSQL
_IGN = "ON CONFLICT DO NOTHING" if _BACKEND == "postgres" else "OR IGNORE"


def _exec(conn, sql: str, params=()) -> None:
    """Execute SQL, adapting placeholders for the current backend."""
    from database.db_manager import adapt_sql
    cur = conn.cursor()
    cur.execute(adapt_sql(sql), params)


def _execmany(conn, sql: str, rows) -> None:
    from database.db_manager import adapt_sql
    cur = conn.cursor()
    cur.executemany(adapt_sql(sql), rows)


def _fetchone(conn, sql: str, params=()):
    from database.db_manager import adapt_sql
    cur = conn.cursor()
    cur.execute(adapt_sql(sql), params)
    row = cur.fetchone()
    return dict(row) if row else None


def seed_roles(conn) -> None:
    _execmany(conn,
        f"INSERT {_IGN} INTO roles (role_name) VALUES (?)",
        [("operator",), ("admin",)],
    )


def seed_shifts(conn) -> None:
    _execmany(conn,
        f"INSERT {_IGN} INTO shifts (shift_name, start_time, end_time) VALUES (?, ?, ?)",
        [
            ("Shift A", "06:00", "14:00"),
            ("Shift B", "14:00", "22:00"),
            ("Shift C", "22:00", "06:00"),
        ],
    )


def seed_users(conn) -> None:
    operator_role = _fetchone(conn, "SELECT role_id FROM roles WHERE role_name = 'operator'")
    admin_role    = _fetchone(conn, "SELECT role_id FROM roles WHERE role_name = 'admin'")
    shift_b       = _fetchone(conn, "SELECT shift_id FROM shifts WHERE shift_name = 'Shift B'")

    if not operator_role or not admin_role or not shift_b:
        logger.warning("Roles or shifts not seeded yet — skipping users")
        return

    demo_accounts = [
        ("operator1", "operator123", "Rahul Sharma",  operator_role["role_id"], shift_b["shift_id"]),
        ("admin1",    "admin123",    "Priya Nair",     admin_role["role_id"],    shift_b["shift_id"]),
    ]

    for username, password, full_name, role_id, shift_id in demo_accounts:
        salt = username
        password_hash = AuthService.hash_password(password, salt)
        _exec(conn,
            f"INSERT {_IGN} INTO users "
            "(username, password_hash, salt, full_name, role_id, shift_id) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (username, password_hash, salt, full_name, role_id, shift_id),
        )


def seed_machines(conn) -> None:
    _execmany(conn,
        f"INSERT {_IGN} INTO machines (machine_name, machine_type, default_stage) VALUES (?, ?, ?)",
        [
            ("Forge press 01",       "Forge Press",             "Forging"),
            ("CNC lathe 04",         "CNC Lathe",               "Machining"),
            ("Heat treat 02",        "Heat Treatment Furnace",  "Heat Treatment"),
            ("Inspection station 01","Inspection Station",      "Quality Inspection"),
            ("Packing line 01",      "Packing Station",         "Packing"),
        ],
    )


def seed_component_types(conn) -> None:
    # Migrate old names if present
    for old, new, desc in [
        ("Push Rod",     "Screw",        "High-precision industrial machine screw"),
        ("Rocker Arm",   "Casting",      "Heavy-duty metal casting part"),
        ("Valve Bridge", "Hex Bolt",     "High-tensile alloy hex bolt"),
        ("Tappet",       "Bearing Ring", "Precision ball bearing inner ring"),
        ("Injector Clamp","Flange Plate","Hydraulic mounting flange plate"),
    ]:
        _exec(conn,
            "UPDATE component_types SET component_name = ?, description = ? WHERE component_name = ?",
            (new, desc, old),
        )

    _execmany(conn,
        f"INSERT {_IGN} INTO component_types (component_name, description, target_cycle_time_sec) VALUES (?, ?, ?)",
        [
            ("Screw",        "High-precision industrial machine screw", 40),
            ("Casting",      "Heavy-duty metal casting part",           60),
            ("Hex Bolt",     "High-tensile alloy hex bolt",             35),
            ("Bearing Ring", "Precision ball bearing inner ring",       45),
            ("Flange Plate", "Hydraulic mounting flange plate",         50),
        ],
    )


def seed_defect_types(conn) -> None:
    _execmany(conn,
        f"INSERT {_IGN} INTO defect_types (defect_name, description, severity) VALUES (?, ?, ?)",
        [
            ("Surface scratch",  "Visible scratch on the machined surface",   "minor"),
            ("Crack",            "Structural crack, often near stress points", "critical"),
            ("Pitting",          "Small surface cavities from casting defects","moderate"),
            ("Discoloration",    "Heat-treatment discoloration outside spec",  "minor"),
            ("Deformation",      "Bent or warped out of tolerance",            "critical"),
        ],
    )


def seed_ai_model(conn) -> None:
    _exec(conn,
        f"INSERT {_IGN} INTO ai_models "
        "(model_name, version, framework, file_path, is_active, notes) VALUES (?, ?, ?, ?, ?, ?)",
        (
            "mobilenetv2-defect-classifier", "0.1.0-prototype", "tensorflow",
            "models/mobilenetv2_defect_classifier_v0.1.0.keras", 1,
            "Prototype. See docs/ML_Pipeline.md for retraining instructions.",
        ),
    )


def seed_app_settings(conn) -> None:
    _execmany(conn,
        f"INSERT {_IGN} INTO app_settings (setting_key, setting_value) VALUES (?, ?)",
        [
            ("default_confidence_threshold",     "0.75"),
            ("qi_units_per_batch_stage_advance",  "25"),
        ],
    )


def run_seed() -> None:
    """Apply seed data idempotently. Caller must ensure database is initialized first."""
    with transaction() as conn:
        seed_roles(conn)
        seed_shifts(conn)
        seed_users(conn)
        seed_machines(conn)
        seed_component_types(conn)
        seed_defect_types(conn)
        seed_ai_model(conn)
        seed_app_settings(conn)
    logger.info("Seed data applied successfully.")


if __name__ == "__main__":
    initialize_database()
    run_seed()
