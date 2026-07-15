"""
Batch service.

Owns all business rules around a production batch's lifecycle: creating
batches, validating stage transitions, and computing completion. The
service never runs raw SQL — every read/write goes through
BatchRepositoryInterface.
"""

import logging
from dataclasses import dataclass
from datetime import datetime

from core.repositories.batch_repository import VALID_STAGES, BatchRepositoryInterface, StageHistoryEntry
from core.services.exceptions import InvalidStageTransitionError, NotFoundError, ValidationError

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class BatchSummary:
    """Domain object returned to the UI — adds computed fields the raw BatchRecord doesn't have."""

    batch_id: int
    batch_code: str
    component_id: int
    planned_quantity: int
    actual_quantity: int
    current_stage: str
    status: str
    completion_percent: float


class BatchService:
    """Business logic for production batches. Depends only on the repository interface."""

    def __init__(self, batch_repository: BatchRepositoryInterface) -> None:
        self._batch_repository = batch_repository

    def create_batch(self, component_id: int, planned_quantity: int) -> BatchSummary:
        """
        Create a new batch with an auto-generated, sortable batch code
        (GPP-<year>-<sequence>). Starts at the Forging stage per the
        Phase 2 lifecycle model.
        """
        if planned_quantity <= 0:
            raise ValidationError("planned_quantity must be a positive integer.")

        year = datetime.now().year
        sequence = len(self._batch_repository.list_all()) + 1
        batch_code = f"GPP-{year}-{sequence:04d}"

        batch_id = self._batch_repository.create(batch_code, component_id, planned_quantity)
        logger.info("Created batch %s (id=%s) for component %s", batch_code, batch_id, component_id)
        return self.get_batch(batch_id)

    def get_batch(self, batch_id: int) -> BatchSummary:
        record = self._batch_repository.get_by_id(batch_id)
        if record is None:
            raise NotFoundError(f"No batch with id {batch_id}.")
        return self._to_summary(record)

    def get_batch_by_code(self, batch_code: str) -> BatchSummary:
        record = self._batch_repository.get_by_code(batch_code)
        if record is None:
            raise NotFoundError(f"No batch with code '{batch_code}'.")
        return self._to_summary(record)

    def list_batches_at_stage(self, stage: str) -> list[BatchSummary]:
        return [self._to_summary(r) for r in self._batch_repository.list_by_stage(stage)]

    def list_all_batches(self) -> list[BatchSummary]:
        return [self._to_summary(r) for r in self._batch_repository.list_all()]

    def count_by_status(self) -> dict[str, int]:
        return self._batch_repository.count_by_status()

    def advance_stage(
        self,
        batch_id: int,
        target_stage: str,
        machine_id: int | None = None,
        operator_id: int | None = None,
        is_simulated: bool = True,
    ) -> BatchSummary:
        """
        Move a batch to the next stage in the lifecycle.

        Only the immediate next stage is a legal transition — this MVP
        models a strictly linear lifecycle (no rework loops, no skipping
        stages). See docs/FutureScope.md for why a rework path isn't
        implemented yet.
        """
        batch = self.get_batch(batch_id)
        self._validate_transition(batch.current_stage, target_stage)

        self._batch_repository.advance_stage(
            batch_id, target_stage, is_simulated=is_simulated, machine_id=machine_id, operator_id=operator_id
        )

        if target_stage == "Dispatch":
            self._batch_repository.mark_completed(batch_id)
            logger.info("Batch %s reached Dispatch and was marked Completed.", batch_id)

        return self.get_batch(batch_id)

    def record_inspection_result(self, batch_id: int) -> BatchSummary:
        """Increment a batch's actual_quantity after an inspection is recorded against it."""
        self._batch_repository.increment_actual_quantity(batch_id, amount=1)
        return self.get_batch(batch_id)

    def get_stage_history(self, batch_id: int) -> list[StageHistoryEntry]:
        return self._batch_repository.get_stage_history(batch_id)

    @staticmethod
    def _validate_transition(current_stage: str, target_stage: str) -> None:
        if target_stage not in VALID_STAGES:
            raise ValidationError(f"'{target_stage}' is not a recognized stage.")

        current_index = VALID_STAGES.index(current_stage)
        target_index = VALID_STAGES.index(target_stage)

        if target_index != current_index + 1:
            raise InvalidStageTransitionError(
                f"Cannot move a batch from '{current_stage}' to '{target_stage}'. "
                f"Only the next stage ('{VALID_STAGES[current_index + 1] if current_index + 1 < len(VALID_STAGES) else 'none — already at Dispatch'}') is a legal transition."
            )

    @staticmethod
    def _to_summary(record) -> BatchSummary:
        completion = (record.actual_quantity / record.planned_quantity * 100) if record.planned_quantity else 0.0
        return BatchSummary(
            batch_id=record.batch_id,
            batch_code=record.batch_code,
            component_id=record.component_id,
            planned_quantity=record.planned_quantity,
            actual_quantity=record.actual_quantity,
            current_stage=record.current_stage,
            status=record.status,
            completion_percent=round(min(completion, 100.0), 1),
        )
