"""Component type repository."""

from abc import ABC, abstractmethod
from dataclasses import dataclass

from core.repositories.base_repository import BaseSqliteRepository


@dataclass(frozen=True)
class ComponentTypeRecord:
    component_id: int
    component_name: str
    description: str
    target_cycle_time_sec: int | None
    is_active: bool = True


class ComponentTypeRepositoryInterface(ABC):
    @abstractmethod
    def get_all(self, active_only: bool = False) -> list[ComponentTypeRecord]:
        raise NotImplementedError

    @abstractmethod
    def get_by_id(self, component_id: int) -> ComponentTypeRecord | None:
        raise NotImplementedError

    @abstractmethod
    def create(self, component_name: str, description: str, target_cycle_time_sec: int | None) -> int:
        raise NotImplementedError

    @abstractmethod
    def update(self, component_id: int, component_name: str, description: str, target_cycle_time_sec: int | None) -> None:
        raise NotImplementedError

    @abstractmethod
    def set_active(self, component_id: int, is_active: bool) -> None:
        raise NotImplementedError


class SqliteComponentTypeRepository(ComponentTypeRepositoryInterface, BaseSqliteRepository):
    def get_all(self, active_only: bool = False) -> list[ComponentTypeRecord]:
        query = "SELECT * FROM component_types" + (" WHERE is_active = 1" if active_only else "") + " ORDER BY component_name"
        rows = self._fetch_all(query)
        return [self._to_record(row) for row in rows]

    def get_by_id(self, component_id: int) -> ComponentTypeRecord | None:
        row = self._fetch_one("SELECT * FROM component_types WHERE component_id = ?", (component_id,))
        return self._to_record(row) if row else None

    def create(self, component_name: str, description: str, target_cycle_time_sec: int | None) -> int:
        return self._execute(
            "INSERT INTO component_types (component_name, description, target_cycle_time_sec) VALUES (?, ?, ?)",
            (component_name, description, target_cycle_time_sec),
        )

    def update(self, component_id: int, component_name: str, description: str, target_cycle_time_sec: int | None) -> None:
        self._execute(
            "UPDATE component_types SET component_name = ?, description = ?, target_cycle_time_sec = ? WHERE component_id = ?",
            (component_name, description, target_cycle_time_sec, component_id),
        )

    def set_active(self, component_id: int, is_active: bool) -> None:
        self._execute(
            "UPDATE component_types SET is_active = ? WHERE component_id = ?",
            (int(is_active), component_id),
        )

    @staticmethod
    def _to_record(row) -> ComponentTypeRecord:
        return ComponentTypeRecord(
            component_id=row["component_id"],
            component_name=row["component_name"],
            description=row["description"],
            target_cycle_time_sec=row["target_cycle_time_sec"],
            is_active=bool(row["is_active"]) if "is_active" in row.keys() else True,
        )
