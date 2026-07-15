"""Production batch repository."""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional

from core.repositories.base_repository import BaseSqliteRepository
from database.db_manager import transaction

logger = logging.getLogger(__name__)

VALID_STAGES = ["Forging", "Machining", "Heat Treatment", "Quality Inspection", "Packing", "Dispatch"]


@dataclass(frozen=True)
class BatchRecord:
    batch_id: int
    batch_code: str
    component_id: int
    planned_quantity: int
    actual_quantity: int
    current_stage: str
    status: str


@dataclass(frozen=True)
class StageHistoryEntry:
    history_id: int
    stage: str
    machine_id: Optional[int]
    operator_id: Optional[int]
    entered_at: str
    exited_at: Optional[str]
    is_simulated: bool


class BatchRepositoryInterface(ABC):
    @abstractmethod
    def create(self, batch_code: str, component_id: int, planned_quantity: int) -> int:
        raise NotImplementedError

    @abstractmethod
    def get_by_code(self, batch_code: str) -> Optional[BatchRecord]:
        raise NotImplementedError

    @abstractmethod
    def get_by_id(self, batch_id: int) -> Optional[BatchRecord]:
        raise NotImplementedError

    @abstractmethod
    def list_by_stage(self, stage: str) -> list[BatchRecord]:
        raise NotImplementedError

    @abstractmethod
    def list_all(self) -> list[BatchRecord]:
        raise NotImplementedError

    @abstractmethod
    def get_stage_history(self, batch_id: int) -> list["StageHistoryEntry"]:
        raise NotImplementedError

    @abstractmethod
    def count_by_status(self) -> dict[str, int]:
        raise NotImplementedError

    @abstractmethod
    def increment_actual_quantity(self, batch_id: int, amount: int = 1) -> None:
        raise NotImplementedError

    @abstractmethod
    def mark_completed(self, batch_id: int) -> None:
        raise NotImplementedError

    @abstractmethod
    def advance_stage(
        self,
        batch_id: int,
        new_stage: str,
        is_simulated: bool = True,
        machine_id: Optional[int] = None,
        operator_id: Optional[int] = None,
    ) -> None:
        raise NotImplementedError


class SqliteBatchRepository(BatchRepositoryInterface, BaseSqliteRepository):
    def create(self, batch_code: str, component_id: int, planned_quantity: int) -> int:
        return self._execute(
            """
            INSERT INTO production_batches (batch_code, component_id, planned_quantity)
            VALUES (?, ?, ?)
            """,
            (batch_code, component_id, planned_quantity),
        )

    def get_by_code(self, batch_code: str) -> Optional[BatchRecord]:
        row = self._fetch_one("SELECT * FROM production_batches WHERE batch_code = ?", (batch_code,))
        return self._to_record(row) if row else None

    def get_by_id(self, batch_id: int) -> Optional[BatchRecord]:
        row = self._fetch_one("SELECT * FROM production_batches WHERE batch_id = ?", (batch_id,))
        return self._to_record(row) if row else None

    def list_by_stage(self, stage: str) -> list[BatchRecord]:
        rows = self._fetch_all(
            "SELECT * FROM production_batches WHERE current_stage = ? AND status = 'In Progress' ORDER BY created_at",
            (stage,),
        )
        return [self._to_record(row) for row in rows]

    def list_all(self) -> list[BatchRecord]:
        rows = self._fetch_all("SELECT * FROM production_batches ORDER BY created_at DESC")
        return [self._to_record(row) for row in rows]

    def count_by_status(self) -> dict[str, int]:
        rows = self._fetch_all("SELECT status, COUNT(*) AS count FROM production_batches GROUP BY status")
        return {row["status"]: row["count"] for row in rows}

    def increment_actual_quantity(self, batch_id: int, amount: int = 1) -> None:
        """Increment a batch's actual_quantity, e.g. after each inspection is recorded."""
        self._execute(
            "UPDATE production_batches SET actual_quantity = actual_quantity + ?, updated_at = datetime('now') WHERE batch_id = ?",
            (amount, batch_id),
        )

    def mark_completed(self, batch_id: int) -> None:
        """Mark a batch's status as Completed (distinct from its stage, which tracks Dispatch separately)."""
        self._execute(
            "UPDATE production_batches SET status = 'Completed', updated_at = datetime('now') WHERE batch_id = ?",
            (batch_id,),
        )

    def get_stage_history(self, batch_id: int) -> list[StageHistoryEntry]:
        rows = self._fetch_all(
            "SELECT * FROM batch_stage_history WHERE batch_id = ? ORDER BY entered_at", (batch_id,)
        )
        return [
            StageHistoryEntry(
                history_id=row["history_id"],
                stage=row["stage"],
                machine_id=row["machine_id"],
                operator_id=row["operator_id"],
                entered_at=row["entered_at"],
                exited_at=row["exited_at"],
                is_simulated=bool(row["is_simulated"]),
            )
            for row in rows
        ]

    def advance_stage(
        self,
        batch_id: int,
        new_stage: str,
        is_simulated: bool = True,
        machine_id: Optional[int] = None,
        operator_id: Optional[int] = None,
    ) -> None:
        """
        Move a batch to a new stage and record the transition.

        Closes the batch's previous open history row (sets `exited_at`)
        before opening the new one — without this, `machine_service` and
        `dashboard_service` have no way to tell an in-progress stage from
        a finished one, since every row would stay open forever.

        All writes happen in one transaction — a batch should never end
        up with `current_stage` updated but no corresponding history row,
        or vice versa.
        """
        if new_stage not in VALID_STAGES:
            raise ValueError(f"Unknown stage '{new_stage}'. Expected one of {VALID_STAGES}.")

        with transaction() as conn:
            conn.execute(
                """
                UPDATE batch_stage_history SET exited_at = datetime('now')
                WHERE batch_id = ? AND exited_at IS NULL
                """,
                (batch_id,),
            )
            conn.execute(
                "UPDATE production_batches SET current_stage = ?, updated_at = datetime('now') WHERE batch_id = ?",
                (new_stage, batch_id),
            )
            conn.execute(
                """
                INSERT INTO batch_stage_history (batch_id, stage, machine_id, operator_id, is_simulated)
                VALUES (?, ?, ?, ?, ?)
                """,
                (batch_id, new_stage, machine_id, operator_id, int(is_simulated)),
            )
        logger.info("Batch %s advanced to stage '%s' (simulated=%s)", batch_id, new_stage, is_simulated)

    @staticmethod
    def _to_record(row) -> BatchRecord:
        return BatchRecord(
            batch_id=row["batch_id"],
            batch_code=row["batch_code"],
            component_id=row["component_id"],
            planned_quantity=row["planned_quantity"],
            actual_quantity=row["actual_quantity"],
            current_stage=row["current_stage"],
            status=row["status"],
        )
