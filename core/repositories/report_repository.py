"""Report and application settings repositories."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional

from core.repositories.base_repository import BaseSqliteRepository


@dataclass(frozen=True)
class ReportRecord:
    report_id: int
    generated_by: int
    report_type: str
    file_path: str
    generated_at: str


class ReportRepositoryInterface(ABC):
    @abstractmethod
    def create(self, generated_by: int, report_type: str, date_start: str, date_end: str, file_path: str) -> int:
        raise NotImplementedError

    @abstractmethod
    def list_all(self) -> list[ReportRecord]:
        raise NotImplementedError


class SqliteReportRepository(ReportRepositoryInterface, BaseSqliteRepository):
    def create(self, generated_by: int, report_type: str, date_start: str, date_end: str, file_path: str) -> int:
        return self._execute(
            """
            INSERT INTO reports (generated_by, report_type, date_range_start, date_range_end, file_path)
            VALUES (?, ?, ?, ?, ?)
            """,
            (generated_by, report_type, date_start, date_end, file_path),
        )

    def list_all(self) -> list[ReportRecord]:
        rows = self._fetch_all("SELECT * FROM reports ORDER BY generated_at DESC")
        return [
            ReportRecord(
                report_id=row["report_id"],
                generated_by=row["generated_by"],
                report_type=row["report_type"],
                file_path=row["file_path"],
                generated_at=row["generated_at"],
            )
            for row in rows
        ]


class SettingsRepositoryInterface(ABC):
    @abstractmethod
    def get(self, key: str) -> Optional[str]:
        raise NotImplementedError

    @abstractmethod
    def set(self, key: str, value: str, updated_by: Optional[int] = None) -> None:
        raise NotImplementedError

    @abstractmethod
    def get_all(self) -> dict[str, str]:
        raise NotImplementedError


class SqliteSettingsRepository(SettingsRepositoryInterface, BaseSqliteRepository):
    def get(self, key: str) -> Optional[str]:
        row = self._fetch_one("SELECT setting_value FROM app_settings WHERE setting_key = ?", (key,))
        return row["setting_value"] if row else None

    def set(self, key: str, value: str, updated_by: Optional[int] = None) -> None:
        self._execute(
            """
            INSERT INTO app_settings (setting_key, setting_value, updated_at, updated_by)
            VALUES (?, ?, datetime('now'), ?)
            ON CONFLICT(setting_key) DO UPDATE SET
                setting_value = excluded.setting_value,
                updated_at = excluded.updated_at,
                updated_by = excluded.updated_by
            """,
            (key, value, updated_by),
        )

    def get_all(self) -> dict[str, str]:
        rows = self._fetch_all("SELECT setting_key, setting_value FROM app_settings")
        return {row["setting_key"]: row["setting_value"] for row in rows}
