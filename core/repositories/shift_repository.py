"""Shift repository."""

from abc import ABC, abstractmethod
from dataclasses import dataclass

from core.repositories.base_repository import BaseSqliteRepository


@dataclass(frozen=True)
class ShiftRecord:
    shift_id: int
    shift_name: str
    start_time: str
    end_time: str


class ShiftRepositoryInterface(ABC):
    @abstractmethod
    def get_all(self) -> list[ShiftRecord]:
        raise NotImplementedError


class SqliteShiftRepository(ShiftRepositoryInterface, BaseSqliteRepository):
    def get_all(self) -> list[ShiftRecord]:
        rows = self._fetch_all("SELECT * FROM shifts ORDER BY start_time")
        return [
            ShiftRecord(
                shift_id=row["shift_id"],
                shift_name=row["shift_name"],
                start_time=row["start_time"],
                end_time=row["end_time"],
            )
            for row in rows
        ]
