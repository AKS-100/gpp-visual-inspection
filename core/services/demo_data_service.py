"""
Demo data service.

Optional, callable separately (never runs automatically) — generates a
realistic manufacturing scenario for demonstrations: multiple batches at
different lifecycle stages, real inspections run through the actual
InspectionService (so dashboard stats, batch progression, and stage
history are all internally consistent, not hand-inserted rows that could
drift from what the real workflow would produce).
"""

import logging
import random
from pathlib import Path

from PIL import Image

from core.services.batch_service import BatchService
from core.services.inspection_service import InspectionService
from core.services.machine_service import MachineService

logger = logging.getLogger(__name__)


class DemoDataService:
    """Generates realistic demo data by driving the real service layer, not by inserting raw rows."""

    def __init__(
        self,
        batch_service: BatchService,
        inspection_service: InspectionService,
        machine_service: MachineService,
        component_repository,
        user_repository,
    ) -> None:
        self._batch_service = batch_service
        self._inspection_service = inspection_service
        self._machine_service = machine_service
        self._component_repository = component_repository
        self._user_repository = user_repository

    def generate(
        self,
        num_batches: int = 6,
        inspections_per_batch: int = 15,
        image_dir: Path = Path("data/uploads/demo"),
        seed: int = 7,
    ) -> dict:
        """
        Create `num_batches` batches spread across different lifecycle
        stages, with realistic inspection history for those that reach
        Quality Inspection. Returns a summary dict of what was created.

        Uses synthetic placeholder images (small random-noise JPEGs) since
        this only needs to exercise the workflow end-to-end, not produce
        visually meaningful defect photos.
        """
        random.seed(seed)
        image_dir.mkdir(parents=True, exist_ok=True)

        components = self._component_repository.get_all(active_only=True)
        machines = self._machine_service.get_all_statuses()
        operator = self._user_repository.get_by_username("operator1")

        if not components or not machines or operator is None:
            raise RuntimeError(
                "Demo data requires seeded component types, machines, and the operator1 account. "
                "Run database/seed_data.py first."
            )

        machines_by_stage = {
            stage: [m for m in machines if m.default_stage == stage]
            for stage in ["Machining", "Heat Treatment", "Quality Inspection"]
        }

        created_batches = 0
        created_inspections = 0
        stage_targets = ["Forging", "Machining", "Heat Treatment", "Quality Inspection", "Quality Inspection", "Quality Inspection"]

        for i in range(num_batches):
            component = random.choice(components)
            batch = self._batch_service.create_batch(component.component_id, planned_quantity=random.randint(20, 80))
            created_batches += 1

            target_stage = stage_targets[i % len(stage_targets)]
            for stage in ["Machining", "Heat Treatment", "Quality Inspection"]:
                if stage == target_stage or self._stage_index(stage) < self._stage_index(target_stage):
                    machine_pool = machines_by_stage.get(stage)
                    machine_id = random.choice(machine_pool).machine_id if machine_pool else None
                    batch = self._batch_service.advance_stage(batch.batch_id, stage, machine_id=machine_id)
                if stage == target_stage:
                    break

            if batch.current_stage == "Quality Inspection":
                qi_machine_pool = machines_by_stage.get("Quality Inspection")
                machine_id = random.choice(qi_machine_pool).machine_id if qi_machine_pool else None

                for j in range(inspections_per_batch):
                    image_path = image_dir / f"demo_{batch.batch_code}_{j}.jpg"
                    if not image_path.exists():
                        _write_placeholder_image(image_path, seed=seed + i * 100 + j)

                    self._inspection_service.run_inspection(
                        batch_id=batch.batch_id,
                        component_id=component.component_id,
                        operator_id=operator.user_id,
                        image_path=str(image_path),
                        machine_id=machine_id,
                    )
                    created_inspections += 1

        summary = {"batches_created": created_batches, "inspections_created": created_inspections}
        logger.info("Demo data generated: %s", summary)
        return summary

    @staticmethod
    def _stage_index(stage: str) -> int:
        order = ["Forging", "Machining", "Heat Treatment", "Quality Inspection", "Packing", "Dispatch"]
        return order.index(stage)


def _write_placeholder_image(path: Path, seed: int) -> None:
    """Small synthetic image — the point is exercising the pipeline, not photorealism."""
    rng = random.Random(seed)
    import numpy as np

    array = np.full((96, 96, 3), 120, dtype="uint8")
    noise = np.array([[rng.randint(0, 40) for _ in range(96)] for _ in range(96)], dtype="uint8")
    array[:, :, 0] = np.clip(array[:, :, 0] + noise, 0, 255)
    Image.fromarray(array).save(path)
