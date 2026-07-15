"""
Application-wide configuration.

Every path, constant, and tunable that would otherwise be hardcoded across
the codebase lives here.
"""

import os
from dataclasses import dataclass, field
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# On Streamlit Cloud, use /tmp for writable directories
_ON_CLOUD = bool(os.getenv("DATABASE_URL"))


@dataclass(frozen=True)
class Paths:
    """Filesystem locations used across the application."""

    project_root: Path = PROJECT_ROOT
    theme_css: Path = PROJECT_ROOT / "app" / "styles" / "theme.css"
    theme_dark_css: Path = PROJECT_ROOT / "app" / "styles" / "theme_dark.css"
    database_file: Path = PROJECT_ROOT / "database" / "gpp_inspection.db"
    models_dir: Path = PROJECT_ROOT / "models"
    logs_dir: Path = (Path("/tmp/gpp_logs") if _ON_CLOUD else PROJECT_ROOT / "logs")
    raw_data_dir: Path = PROJECT_ROOT / "data" / "raw"
    processed_data_dir: Path = PROJECT_ROOT / "data" / "processed"
    uploaded_images_dir: Path = (Path("/tmp/gpp_uploads") if _ON_CLOUD else PROJECT_ROOT / "data" / "uploads")


@dataclass(frozen=True)
class SessionKeys:
    user: str = "gpp_user"
    active_page: str = "gpp_active_page"
    selected_batch: str = "gpp_selected_batch"
    theme_mode: str = "gpp_theme_mode"


@dataclass(frozen=True)
class AppSettings:
    """Top-level application settings."""

    app_name: str = "GPP visual inspection and manufacturing analytics"
    company_name: str = "Ghaziabad Precision Products Pvt. Ltd."
    default_confidence_threshold: float = 0.75
    qi_units_per_batch_stage_advance: int = 25
    paths: Paths = field(default_factory=Paths)
    session_keys: SessionKeys = field(default_factory=SessionKeys)


settings = AppSettings()
