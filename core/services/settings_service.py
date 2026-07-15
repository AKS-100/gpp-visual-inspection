"""
Settings service.

Provides typed getters/setters over the app_settings key-value table so
callers don't scatter string-to-number parsing (and validation) across
every consumer of a setting.
"""

import logging

from core.repositories.report_repository import SettingsRepositoryInterface
from core.services.exceptions import ValidationError

logger = logging.getLogger(__name__)

_CONFIDENCE_THRESHOLD_KEY = "default_confidence_threshold"
_QI_UNITS_PER_STAGE_ADVANCE_KEY = "qi_units_per_batch_stage_advance"


class SettingsService:
    """Typed access to application settings. Depends only on the repository interface."""

    def __init__(self, settings_repository: SettingsRepositoryInterface) -> None:
        self._settings_repository = settings_repository

    def get_confidence_threshold(self) -> float:
        raw = self._settings_repository.get(_CONFIDENCE_THRESHOLD_KEY)
        return float(raw) if raw is not None else 0.75

    def set_confidence_threshold(self, value: float, updated_by: int | None = None) -> None:
        if not (0.0 <= value <= 1.0):
            raise ValidationError("Confidence threshold must be between 0.0 and 1.0.")
        self._settings_repository.set(_CONFIDENCE_THRESHOLD_KEY, str(value), updated_by)
        logger.info("Confidence threshold updated to %.2f", value)

    def get_qi_units_per_stage_advance(self) -> int:
        raw = self._settings_repository.get(_QI_UNITS_PER_STAGE_ADVANCE_KEY)
        return int(raw) if raw is not None else 25

    def set_qi_units_per_stage_advance(self, value: int, updated_by: int | None = None) -> None:
        if value <= 0:
            raise ValidationError("qi_units_per_batch_stage_advance must be a positive integer.")
        self._settings_repository.set(_QI_UNITS_PER_STAGE_ADVANCE_KEY, str(value), updated_by)
        logger.info("QI units-per-stage-advance updated to %d", value)

    def get_all(self) -> dict[str, str]:
        return self._settings_repository.get_all()

    def reset_to_defaults(self, updated_by: int | None = None) -> None:
        """Reset both known settings to their hardcoded defaults."""
        self.set_confidence_threshold(0.75, updated_by)
        self.set_qi_units_per_stage_advance(25, updated_by)
