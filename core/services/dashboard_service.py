"""
Dashboard service.

Computes every KPI the Dashboard and Factory Overview pages need, from
real inspection/batch/machine data. Returns typed dataclasses rather than
raw dicts so page code gets attribute access and type checking instead of
string-keyed dict lookups.
"""

import logging
from dataclasses import dataclass
from datetime import date, datetime, timezone

from core.repositories.inspection_repository import InspectionRecord, InspectionRepositoryInterface
from core.services.batch_service import BatchService
from core.services.machine_service import MachineService

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class DashboardSummary:
    total_inspections: int
    accepted_count: int
    rejected_count: int
    acceptance_rate: float
    defect_rate: float
    today_production: int


@dataclass(frozen=True)
class TrendPoint:
    date: str
    good_count: int
    defective_count: int


@dataclass(frozen=True)
class RecentInspectionView:
    inspection_id: int
    batch_id: int
    prediction: str
    confidence_score: float
    inspected_at: str


class DashboardService:
    """
    Computes dashboard KPIs. Depends on InspectionRepositoryInterface
    directly (read-only aggregate queries) and MachineService for the
    utilization proxy metric.
    """

    def __init__(
        self,
        inspection_repository: InspectionRepositoryInterface,
        machine_service: MachineService,
        batch_service: BatchService,
    ) -> None:
        self._inspection_repository = inspection_repository
        self._machine_service = machine_service
        self._batch_service = batch_service

    def get_summary(self) -> DashboardSummary:
        counts = self._inspection_repository.count_by_prediction_since("2000-01-01")  # effectively "all time"
        accepted = counts["GOOD"]
        rejected = counts["DEFECTIVE"]
        total = accepted + rejected

        acceptance_rate = round((accepted / total * 100), 1) if total else 0.0
        defect_rate = round((rejected / total * 100), 1) if total else 0.0

        today = datetime.now(timezone.utc).date().isoformat()
        today_counts = self._inspection_repository.count_by_prediction_since(today)
        today_production = today_counts["GOOD"] + today_counts["DEFECTIVE"]

        return DashboardSummary(
            total_inspections=total,
            accepted_count=accepted,
            rejected_count=rejected,
            acceptance_rate=acceptance_rate,
            defect_rate=defect_rate,
            today_production=today_production,
        )

    def get_trend(self, days: int = 7) -> list[TrendPoint]:
        rows = self._inspection_repository.count_by_day(days)
        return [TrendPoint(date=d, good_count=g, defective_count=b) for d, g, b in rows]

    def get_defect_breakdown(self) -> dict[str, int]:
        """Defect type -> count, for a Pareto chart. Empty dict if no defects logged yet."""
        return self._inspection_repository.get_defect_breakdown()

    def get_recent_inspections(self, limit: int = 20) -> list[RecentInspectionView]:
        records: list[InspectionRecord] = self._inspection_repository.list_recent(limit)
        return [
            RecentInspectionView(
                inspection_id=r.inspection_id,
                batch_id=r.batch_id,
                prediction=r.prediction,
                confidence_score=r.confidence_score,
                inspected_at=r.inspected_at,
            )
            for r in records
        ]

    def get_machine_utilization(self) -> dict[str, int]:
        """Delegates to MachineService's stage-history-count proxy metric."""
        return self._machine_service.utilization_summary()

    def get_batch_statistics(self) -> dict[str, int]:
        """Batch counts grouped by status (In Progress / Completed / On Hold)."""
        return self._batch_service.count_by_status()
