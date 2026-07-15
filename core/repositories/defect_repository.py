"""Defect type repository."""

from abc import ABC, abstractmethod
from dataclasses import dataclass

from core.repositories.base_repository import BaseSqliteRepository


@dataclass(frozen=True)
class DefectTypeRecord:
    defect_id: int
    defect_name: str
    description: str
    severity: str


class DefectTypeRepositoryInterface(ABC):
    @abstractmethod
    def get_all(self) -> list[DefectTypeRecord]:
        raise NotImplementedError


class SqliteDefectTypeRepository(DefectTypeRepositoryInterface, BaseSqliteRepository):
    def get_all(self) -> list[DefectTypeRecord]:
        rows = self._fetch_all("SELECT * FROM defect_types ORDER BY defect_name")
        return [
            DefectTypeRecord(
                defect_id=row["defect_id"],
                defect_name=row["defect_name"],
                description=row["description"],
                severity=row["severity"],
            )
            for row in rows
        ]
