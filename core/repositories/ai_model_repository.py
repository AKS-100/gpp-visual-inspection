"""AI model registry repository."""

from abc import ABC, abstractmethod
from dataclasses import dataclass

from core.repositories.base_repository import BaseSqliteRepository
from database.db_manager import transaction


@dataclass(frozen=True)
class AiModelRecord:
    model_id: int
    model_name: str
    version: str
    framework: str
    file_path: str
    is_active: bool
    accuracy_metric: float | None


class AiModelRepositoryInterface(ABC):
    @abstractmethod
    def get_active_model(self) -> AiModelRecord | None:
        """
        Return the currently active model.

        MVP scope: exactly one active model at a time, shared across all
        component types. Per-component model routing (via a future
        model_component_types junction table) is documented in
        docs/FutureScope.md rather than implemented here.
        """
        raise NotImplementedError

    @abstractmethod
    def get_all(self) -> list[AiModelRecord]:
        raise NotImplementedError

    @abstractmethod
    def activate_model(self, model_id: int) -> None:
        """Activate this model and deactivate all others (MVP keeps exactly one active model)."""
        raise NotImplementedError

    @abstractmethod
    def deactivate_model(self, model_id: int) -> None:
        raise NotImplementedError

    @abstractmethod
    def create(
        self, model_name: str, version: str, framework: str, file_path: str, notes: str = ""
    ) -> int:
        raise NotImplementedError


class SqliteAiModelRepository(AiModelRepositoryInterface, BaseSqliteRepository):
    def get_active_model(self) -> AiModelRecord | None:
        row = self._fetch_one("SELECT * FROM ai_models WHERE is_active = 1 ORDER BY model_id DESC LIMIT 1")
        return self._to_record(row) if row else None

    def get_all(self) -> list[AiModelRecord]:
        rows = self._fetch_all("SELECT * FROM ai_models ORDER BY model_name, version")
        return [self._to_record(row) for row in rows]

    def activate_model(self, model_id: int) -> None:
        with transaction() as conn:
            conn.execute("UPDATE ai_models SET is_active = 0")
            conn.execute("UPDATE ai_models SET is_active = 1 WHERE model_id = ?", (model_id,))

    def deactivate_model(self, model_id: int) -> None:
        self._execute("UPDATE ai_models SET is_active = 0 WHERE model_id = ?", (model_id,))

    def create(self, model_name: str, version: str, framework: str, file_path: str, notes: str = "") -> int:
        return self._execute(
            """
            INSERT INTO ai_models (model_name, version, framework, file_path, is_active, notes)
            VALUES (?, ?, ?, ?, 0, ?)
            """,
            (model_name, version, framework, file_path, notes),
        )

    @staticmethod
    def _to_record(row) -> AiModelRecord:
        return AiModelRecord(
            model_id=row["model_id"],
            model_name=row["model_name"],
            version=row["version"],
            framework=row["framework"],
            file_path=row["file_path"],
            is_active=bool(row["is_active"]),
            accuracy_metric=row["accuracy_metric"],
        )
