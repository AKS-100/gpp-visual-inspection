"""Machine repository."""

from abc import ABC, abstractmethod
from dataclasses import dataclass

from core.repositories.base_repository import BaseSqliteRepository


@dataclass(frozen=True)
class MachineRecord:
    machine_id: int
    machine_name: str
    machine_type: str
    default_stage: str
    is_active: bool


class MachineRepositoryInterface(ABC):
    @abstractmethod
    def get_all(self, active_only: bool = True) -> list[MachineRecord]:
        raise NotImplementedError

    @abstractmethod
    def get_by_id(self, machine_id: int) -> MachineRecord | None:
        raise NotImplementedError

    @abstractmethod
    def get_by_stage(self, stage: str) -> list[MachineRecord]:
        raise NotImplementedError

    @abstractmethod
    def get_stage_history_counts(self) -> dict[int, int]:
        raise NotImplementedError

    @abstractmethod
    def is_machine_busy(self, machine_id: int) -> bool:
        raise NotImplementedError

    @abstractmethod
    def create(self, machine_name: str, machine_type: str, default_stage: str) -> int:
        raise NotImplementedError

    @abstractmethod
    def update(self, machine_id: int, machine_name: str, machine_type: str, default_stage: str) -> None:
        raise NotImplementedError

    @abstractmethod
    def set_active(self, machine_id: int, is_active: bool) -> None:
        raise NotImplementedError


class SqliteMachineRepository(MachineRepositoryInterface, BaseSqliteRepository):
    def get_all(self, active_only: bool = True) -> list[MachineRecord]:
        query = "SELECT * FROM machines" + (" WHERE is_active = 1" if active_only else "") + " ORDER BY machine_name"
        rows = self._fetch_all(query)
        return [self._to_record(row) for row in rows]

    def get_by_id(self, machine_id: int) -> MachineRecord | None:
        row = self._fetch_one("SELECT * FROM machines WHERE machine_id = ?", (machine_id,))
        return self._to_record(row) if row else None

    def get_by_stage(self, stage: str) -> list[MachineRecord]:
        rows = self._fetch_all(
            "SELECT * FROM machines WHERE default_stage = ? AND is_active = 1 ORDER BY machine_name",
            (stage,),
        )
        return [self._to_record(row) for row in rows]

    def get_stage_history_counts(self) -> dict[int, int]:
        """
        Number of batch_stage_history rows referencing each machine — a
        simplified utilization proxy for the MVP. Real machine telemetry
        (actual running time, idle time) requires the machine-status
        simulation built in a later phase; see docs/FutureScope.md.
        """
        rows = self._fetch_all(
            "SELECT machine_id, COUNT(*) AS count FROM batch_stage_history WHERE machine_id IS NOT NULL GROUP BY machine_id"
        )
        return {row["machine_id"]: row["count"] for row in rows}

    def is_machine_busy(self, machine_id: int) -> bool:
        """True if this machine has an open (not yet exited) stage-history entry right now."""
        row = self._fetch_one(
            "SELECT 1 FROM batch_stage_history WHERE machine_id = ? AND exited_at IS NULL LIMIT 1",
            (machine_id,),
        )
        return row is not None

    def create(self, machine_name: str, machine_type: str, default_stage: str) -> int:
        return self._execute(
            "INSERT INTO machines (machine_name, machine_type, default_stage) VALUES (?, ?, ?)",
            (machine_name, machine_type, default_stage),
        )

    def update(self, machine_id: int, machine_name: str, machine_type: str, default_stage: str) -> None:
        self._execute(
            "UPDATE machines SET machine_name = ?, machine_type = ?, default_stage = ? WHERE machine_id = ?",
            (machine_name, machine_type, default_stage, machine_id),
        )

    def set_active(self, machine_id: int, is_active: bool) -> None:
        self._execute(
            "UPDATE machines SET is_active = ? WHERE machine_id = ?",
            (int(is_active), machine_id),
        )

    @staticmethod
    def _to_record(row) -> MachineRecord:
        return MachineRecord(
            machine_id=row["machine_id"],
            machine_name=row["machine_name"],
            machine_type=row["machine_type"],
            default_stage=row["default_stage"],
            is_active=bool(row["is_active"]),
        )
