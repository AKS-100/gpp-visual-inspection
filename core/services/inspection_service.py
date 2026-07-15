"""
Inspection service.

Orchestrates the full inspection workflow: validate batch/machine/
component, run inference via AIInferenceEngine (today: DummyInferenceEngine,
later: TensorFlowInferenceEngine — this service does not change either
way), persist the result, and trigger batch progression through
BatchService when the configured threshold is reached.
"""

import logging
from dataclasses import dataclass

from core.ml.inference_engine import AIInferenceEngine
from core.repositories.ai_model_repository import AiModelRepositoryInterface
from core.repositories.inspection_repository import InspectionRepositoryInterface
from core.services.batch_service import BatchService
from core.services.exceptions import ValidationError
from core.services.settings_service import SettingsService

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class InspectionOutcome:
    """Result of running one inspection, returned to the UI."""

    inspection_id: int
    prediction: str
    confidence_score: float
    defect_ids: list[int]
    heatmap_path: str | None
    batch_current_stage: str
    batch_advanced: bool


class InspectionService:
    """
    Orchestrates the inspection workflow.

    Depends on BatchService (not BatchRepository directly) for stage
    progression — batch lifecycle rules belong in BatchService, and
    InspectionService should not need to know what a legal transition is.
    """

    def __init__(
        self,
        inspection_repository: InspectionRepositoryInterface,
        ai_model_repository: AiModelRepositoryInterface,
        batch_service: BatchService,
        settings_service: SettingsService,
        ai_engine: AIInferenceEngine,
    ) -> None:
        self._inspection_repository = inspection_repository
        self._ai_model_repository = ai_model_repository
        self._batch_service = batch_service
        self._settings_service = settings_service
        self._ai_engine = ai_engine

    def run_inspection(
        self,
        batch_id: int,
        component_id: int,
        operator_id: int,
        image_path: str,
        machine_id: int | None = None,
        shift_id: int | None = None,
    ) -> InspectionOutcome:
        """
        Run the full inspection workflow for one uploaded image.

        Raises:
            ValidationError: if the batch's component doesn't match the
                selected component, or the batch isn't at the Quality
                Inspection stage, or no AI model is registered as active.
            NotFoundError: if batch_id doesn't exist (raised by BatchService).
        """
        batch = self._batch_service.get_batch(batch_id)

        if batch.component_id != component_id:
            raise ValidationError(
                f"Batch {batch.batch_code} is for component {batch.component_id}, not {component_id}."
            )
        if batch.current_stage != "Quality Inspection":
            raise ValidationError(
                f"Batch {batch.batch_code} is at stage '{batch.current_stage}', not Quality Inspection. "
                "Inspections can only be recorded once a batch reaches Quality Inspection."
            )

        active_model = self._ai_model_repository.get_active_model()
        if active_model is None:
            raise ValidationError("No active AI model is registered. An admin must activate a model first.")

        result = self._ai_engine.predict(image_path)

        inspection_id = self._inspection_repository.create(
            batch_id=batch_id,
            component_id=component_id,
            operator_id=operator_id,
            model_id=active_model.model_id,
            model_version_snapshot=self._ai_engine.model_version_label,
            image_path=image_path,
            prediction=result.prediction,
            confidence_score=result.confidence_score,
            heatmap_path=result.heatmap_path,
            machine_id=machine_id,
            shift_id=shift_id,
            defect_ids=result.defect_ids,
        )

        updated_batch = self._batch_service.record_inspection_result(batch_id)

        batch_advanced = False
        threshold = self._settings_service.get_qi_units_per_stage_advance()
        if updated_batch.actual_quantity >= threshold and updated_batch.current_stage == "Quality Inspection":
            updated_batch = self._batch_service.advance_stage(batch_id, "Packing", is_simulated=False)
            batch_advanced = True
            logger.info(
                "Batch %s reached %d inspections, auto-advanced to Packing.",
                updated_batch.batch_code, threshold,
            )

        logger.info(
            "Inspection %s recorded for batch %s: %s (%.1f%% confidence)",
            inspection_id, batch.batch_code, result.prediction, result.confidence_score * 100,
        )

        return InspectionOutcome(
            inspection_id=inspection_id,
            prediction=result.prediction,
            confidence_score=result.confidence_score,
            defect_ids=result.defect_ids,
            heatmap_path=result.heatmap_path,
            batch_current_stage=updated_batch.current_stage,
            batch_advanced=batch_advanced,
        )
