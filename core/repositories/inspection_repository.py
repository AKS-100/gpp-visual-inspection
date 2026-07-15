"""Inspection repository."""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional

from core.repositories.base_repository import BaseSqliteRepository
from database.db_manager import transaction

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class InspectionRecord:
    inspection_id: int
    batch_id: int
    component_id: int
    machine_id: Optional[int]
    operator_id: int
    prediction: str
    confidence_score: float
    image_path: str
    heatmap_path: Optional[str]
    inspected_at: str


@dataclass(frozen=True)
class InspectionDetailRecord:
    """Inspection with joined display fields — what the History page actually needs to render."""

    inspection_id: int
    batch_code: str
    component_name: str
    machine_name: str
    operator_name: str
    prediction: str
    confidence_score: float
    inspected_at: str
    image_path: str
    heatmap_path: Optional[str]


class InspectionRepositoryInterface(ABC):
    @abstractmethod
    def create(
        self,
        batch_id: int,
        component_id: int,
        operator_id: int,
        model_id: Optional[int],
        model_version_snapshot: str,
        image_path: str,
        prediction: str,
        confidence_score: float,
        heatmap_path: Optional[str] = None,
        machine_id: Optional[int] = None,
        shift_id: Optional[int] = None,
        defect_ids: Optional[list[int]] = None,
    ) -> int:
        raise NotImplementedError

    @abstractmethod
    def list_by_batch(self, batch_id: int) -> list[InspectionRecord]:
        raise NotImplementedError

    @abstractmethod
    def count_by_batch(self, batch_id: int) -> int:
        raise NotImplementedError

    @abstractmethod
    def list_recent(self, limit: int = 50) -> list[InspectionRecord]:
        raise NotImplementedError

    @abstractmethod
    def count_by_prediction_since(self, since_date: str) -> dict[str, int]:
        raise NotImplementedError

    @abstractmethod
    def count_by_day(self, days: int) -> list[tuple[str, int, int]]:
        raise NotImplementedError

    @abstractmethod
    def get_defect_breakdown(self) -> dict[str, int]:
        raise NotImplementedError

    @abstractmethod
    def search(
        self,
        prediction: Optional[str] = None,
        batch_code: Optional[str] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        confidence_min: Optional[float] = None,
        confidence_max: Optional[float] = None,
        machine_id: Optional[int] = None,
        component_id: Optional[int] = None,
        limit: int = 200,
    ) -> list[InspectionDetailRecord]:
        raise NotImplementedError


class SqliteInspectionRepository(InspectionRepositoryInterface, BaseSqliteRepository):
    def create(
        self,
        batch_id: int,
        component_id: int,
        operator_id: int,
        model_id: Optional[int],
        model_version_snapshot: str,
        image_path: str,
        prediction: str,
        confidence_score: float,
        heatmap_path: Optional[str] = None,
        machine_id: Optional[int] = None,
        shift_id: Optional[int] = None,
        defect_ids: Optional[list[int]] = None,
    ) -> int:
        """
        Insert an inspection and its defect links as a single transaction.

        If the inspection insert succeeds but a defect-link insert fails
        (e.g. a bad defect_id), the whole write rolls back rather than
        leaving a defective-but-unflagged inspection row behind.
        """
        if prediction not in ("GOOD", "DEFECTIVE"):
            raise ValueError(f"prediction must be 'GOOD' or 'DEFECTIVE', got '{prediction}'")

        with transaction() as conn:
            cursor = conn.execute(
                """
                INSERT INTO inspections (
                    batch_id, component_id, machine_id, operator_id, shift_id,
                    model_id, model_version_snapshot, image_path, heatmap_path,
                    prediction, confidence_score
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    batch_id, component_id, machine_id, operator_id, shift_id,
                    model_id, model_version_snapshot, image_path, heatmap_path,
                    prediction, confidence_score,
                ),
            )
            inspection_id = cursor.lastrowid

            for defect_id in defect_ids or []:
                conn.execute(
                    "INSERT INTO inspection_defects (inspection_id, defect_id) VALUES (?, ?)",
                    (inspection_id, defect_id),
                )

        logger.info("Inspection %s recorded: %s (confidence %.3f)", inspection_id, prediction, confidence_score)
        return inspection_id

    def list_by_batch(self, batch_id: int) -> list[InspectionRecord]:
        rows = self._fetch_all(
            "SELECT * FROM inspections WHERE batch_id = ? ORDER BY inspected_at DESC", (batch_id,)
        )
        return [self._to_record(row) for row in rows]

    def count_by_batch(self, batch_id: int) -> int:
        row = self._fetch_one("SELECT COUNT(*) AS c FROM inspections WHERE batch_id = ?", (batch_id,))
        return row["c"] if row else 0

    def list_recent(self, limit: int = 50) -> list[InspectionRecord]:
        rows = self._fetch_all("SELECT * FROM inspections ORDER BY inspected_at DESC LIMIT ?", (limit,))
        return [self._to_record(row) for row in rows]

    def count_by_prediction_since(self, since_date: str) -> dict[str, int]:
        """Count GOOD vs DEFECTIVE inspections since `since_date` (inclusive, 'YYYY-MM-DD')."""
        rows = self._fetch_all(
            """
            SELECT prediction, COUNT(*) AS count
            FROM inspections
            WHERE date(inspected_at) >= date(?)
            GROUP BY prediction
            """,
            (since_date,),
        )
        counts = {"GOOD": 0, "DEFECTIVE": 0}
        counts.update({row["prediction"]: row["count"] for row in rows})
        return counts

    def count_by_day(self, days: int) -> list[tuple[str, int, int]]:
        """
        Return (date, good_count, defective_count) for each of the last
        `days` days, oldest first. Days with zero inspections are
        included as (date, 0, 0) so trend charts don't show gaps.
        """
        rows = self._fetch_all(
            """
            SELECT
                date(inspected_at) AS day,
                SUM(CASE WHEN prediction = 'GOOD' THEN 1 ELSE 0 END) AS good_count,
                SUM(CASE WHEN prediction = 'DEFECTIVE' THEN 1 ELSE 0 END) AS defective_count
            FROM inspections
            WHERE date(inspected_at) >= date('now', ?)
            GROUP BY day
            ORDER BY day
            """,
            (f"-{days - 1} days",),
        )
        by_day = {row["day"]: (row["good_count"], row["defective_count"]) for row in rows}

        from datetime import datetime, timedelta, timezone

        today = datetime.now(timezone.utc).date()
        result = []
        for offset in range(days - 1, -1, -1):
            day = (today - timedelta(days=offset)).isoformat()
            good, defective = by_day.get(day, (0, 0))
            result.append((day, good, defective))
        return result

    def get_defect_breakdown(self) -> dict[str, int]:
        """Count of inspections per defect type name, for a Pareto chart."""
        rows = self._fetch_all(
            """
            SELECT dt.defect_name, COUNT(*) AS count
            FROM inspection_defects id_
            JOIN defect_types dt ON dt.defect_id = id_.defect_id
            GROUP BY dt.defect_name
            ORDER BY count DESC
            """
        )
        return {row["defect_name"]: row["count"] for row in rows}

    def search(
        self,
        prediction: Optional[str] = None,
        batch_code: Optional[str] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        confidence_min: Optional[float] = None,
        confidence_max: Optional[float] = None,
        machine_id: Optional[int] = None,
        component_id: Optional[int] = None,
        limit: int = 200,
    ) -> list[InspectionDetailRecord]:
        """Filtered, joined inspection listing for the History page. All filters are optional and combine with AND."""
        clauses = []
        params: list = []

        if prediction:
            clauses.append("i.prediction = ?")
            params.append(prediction)
        if batch_code:
            clauses.append("pb.batch_code LIKE ?")
            params.append(f"%{batch_code}%")
        if date_from:
            clauses.append("date(i.inspected_at) >= date(?)")
            params.append(date_from)
        if date_to:
            clauses.append("date(i.inspected_at) <= date(?)")
            params.append(date_to)
        if confidence_min is not None:
            clauses.append("i.confidence_score >= ?")
            params.append(confidence_min)
        if confidence_max is not None:
            clauses.append("i.confidence_score <= ?")
            params.append(confidence_max)
        if machine_id is not None:
            clauses.append("i.machine_id = ?")
            params.append(machine_id)
        if component_id is not None:
            clauses.append("i.component_id = ?")
            params.append(component_id)

        where_sql = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        params.append(limit)

        rows = self._fetch_all(
            f"""
            SELECT
                i.inspection_id, pb.batch_code, ct.component_name,
                COALESCE(m.machine_name, 'Unassigned') AS machine_name,
                u.full_name AS operator_name,
                i.prediction, i.confidence_score, i.inspected_at,
                i.image_path, i.heatmap_path
            FROM inspections i
            JOIN production_batches pb ON pb.batch_id = i.batch_id
            JOIN component_types ct ON ct.component_id = i.component_id
            LEFT JOIN machines m ON m.machine_id = i.machine_id
            JOIN users u ON u.user_id = i.operator_id
            {where_sql}
            ORDER BY i.inspected_at DESC
            LIMIT ?
            """,
            params,
        )
        return [
            InspectionDetailRecord(
                inspection_id=row["inspection_id"],
                batch_code=row["batch_code"],
                component_name=row["component_name"],
                machine_name=row["machine_name"],
                operator_name=row["operator_name"],
                prediction=row["prediction"],
                confidence_score=row["confidence_score"],
                inspected_at=row["inspected_at"],
                image_path=row["image_path"],
                heatmap_path=row["heatmap_path"],
            )
            for row in rows
        ]

    @staticmethod
    def _to_record(row) -> InspectionRecord:
        return InspectionRecord(
            inspection_id=row["inspection_id"],
            batch_id=row["batch_id"],
            component_id=row["component_id"],
            machine_id=row["machine_id"],
            operator_id=row["operator_id"],
            prediction=row["prediction"],
            confidence_score=row["confidence_score"],
            image_path=row["image_path"],
            heatmap_path=row["heatmap_path"],
            inspected_at=row["inspected_at"],
        )
