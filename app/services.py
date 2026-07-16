"""
Service container.

Builds every repository and service exactly once per process and hands
pages a single `Services` bundle, so pages never construct repositories
directly and never duplicate wiring logic. Cached via st.cache_resource —
Streamlit reruns the script on every interaction, but this factory only
actually runs once.
"""

from dataclasses import dataclass

import logging
import streamlit as st

from core.ml.inference_engine import AIInferenceEngine, DummyInferenceEngine
from core.repositories.ai_model_repository import AiModelRepositoryInterface, SqliteAiModelRepository
from core.repositories.batch_repository import BatchRepositoryInterface, SqliteBatchRepository
from core.repositories.component_repository import ComponentTypeRepositoryInterface, SqliteComponentTypeRepository
from core.repositories.defect_repository import DefectTypeRepositoryInterface, SqliteDefectTypeRepository
from core.repositories.inspection_repository import InspectionRepositoryInterface, SqliteInspectionRepository
from core.repositories.machine_repository import MachineRepositoryInterface, SqliteMachineRepository
from core.repositories.report_repository import SqliteReportRepository, SqliteSettingsRepository, ReportRepositoryInterface, SettingsRepositoryInterface
from core.repositories.shift_repository import ShiftRepositoryInterface, SqliteShiftRepository
from core.repositories.user_repository import SqliteUserRepository, UserRepositoryInterface
from core.services.batch_service import BatchService
from core.services.dashboard_service import DashboardService
from core.services.demo_data_service import DemoDataService
from core.services.inspection_service import InspectionService
from core.services.machine_service import MachineService
from core.services.report_service import ReportService
from core.services.settings_service import SettingsService
from config.settings import settings
from database.db_manager import initialize_database
from database.seed_data import run_seed


@dataclass(frozen=True)
class Services:
    """Everything a page needs, in one bundle. Pages depend on this, never on repositories directly."""

    batch_service: BatchService
    machine_service: MachineService
    settings_service: SettingsService
    inspection_service: InspectionService
    dashboard_service: DashboardService
    report_service: ReportService
    demo_data_service: DemoDataService

    component_repository: ComponentTypeRepositoryInterface
    defect_repository: DefectTypeRepositoryInterface
    ai_model_repository: AiModelRepositoryInterface
    machine_repository: MachineRepositoryInterface
    user_repository: UserRepositoryInterface
    shift_repository: ShiftRepositoryInterface
    inspection_repository: InspectionRepositoryInterface
    batch_repository: BatchRepositoryInterface
    report_repository: ReportRepositoryInterface

    ai_engine: AIInferenceEngine


def build_ai_engine(defect_ids_pool: list[int]) -> AIInferenceEngine:
    """
    Load the best available inference engine in priority order:
      1. ONNX model  (works on Python 3.14, preferred for cloud deployment)
      2. TensorFlow .keras model (works on Python <=3.12)
      3. DummyInferenceEngine (deterministic stub — always available)
    """
    models_dir = settings.paths.models_dir

    # ── 1. ONNX (Python 3.14 compatible) ──────────────────────────────────
    onnx_path = models_dir / "industrial_quality_classifier.onnx"
    if onnx_path.exists():
        try:
            from core.ml.onnx_inference_engine import ONNXInferenceEngine
            logger.info("Using ONNXInferenceEngine from %s", onnx_path)
            return ONNXInferenceEngine(
                model_path=str(onnx_path),
                version_label=f"onnx-industrial-classifier:{onnx_path.stat().st_mtime_ns}",
            )
        except Exception as exc:
            logger.warning("ONNX engine failed to load (%s) — trying TensorFlow.", exc)

    # ── 2. TensorFlow .keras ───────────────────────────────────────────────
    keras_path = models_dir / "industrial_quality_classifier.keras"
    if keras_path.exists():
        try:
            from core.ml.tensorflow_inference_engine import TensorFlowInferenceEngine
            logger.info("Using TensorFlowInferenceEngine from %s", keras_path)
            return TensorFlowInferenceEngine(
                model_path=str(keras_path),
                version_label=f"efficientnetb0-industrial-classifier:{keras_path.stat().st_mtime_ns}",
            )
        except ImportError:
            logger.warning("Keras model found but TensorFlow not installed — trying ONNX conversion fallback.")

    # ── 3. Dummy stub ──────────────────────────────────────────────────────
    logger.warning("No trained model found — using DummyInferenceEngine.")
    return DummyInferenceEngine(defect_ids_pool=defect_ids_pool)



@st.cache_resource(show_spinner=False)
def get_services() -> Services:
    """Build (once) and return the full service bundle."""
    initialize_database()
    run_seed()  # idempotent — safe to call on every startup

    batch_repository = SqliteBatchRepository()
    machine_repository = SqliteMachineRepository()
    component_repository = SqliteComponentTypeRepository()
    defect_repository = SqliteDefectTypeRepository()
    ai_model_repository = SqliteAiModelRepository()
    inspection_repository = SqliteInspectionRepository()
    settings_repository: SettingsRepositoryInterface = SqliteSettingsRepository()
    user_repository = SqliteUserRepository()
    shift_repository = SqliteShiftRepository()
    report_repository: ReportRepositoryInterface = SqliteReportRepository()

    defect_ids_pool = [d.defect_id for d in defect_repository.get_all()]
    ai_engine = build_ai_engine(defect_ids_pool)

    batch_service = BatchService(batch_repository)
    machine_service = MachineService(machine_repository)
    settings_service = SettingsService(settings_repository)
    dashboard_service = DashboardService(inspection_repository, machine_service, batch_service)
    report_service = ReportService(dashboard_service, machine_service, ai_model_repository, report_repository)
    inspection_service = InspectionService(
        inspection_repository, ai_model_repository, batch_service, settings_service, ai_engine
    )
    demo_data_service = DemoDataService(
        batch_service, inspection_service, machine_service, component_repository, user_repository
    )

    return Services(
        batch_service=batch_service,
        machine_service=machine_service,
        settings_service=settings_service,
        inspection_service=inspection_service,
        dashboard_service=dashboard_service,
        report_service=report_service,
        component_repository=component_repository,
        defect_repository=defect_repository,
        ai_model_repository=ai_model_repository,
        machine_repository=machine_repository,
        user_repository=user_repository,
        shift_repository=shift_repository,
        inspection_repository=inspection_repository,
        batch_repository=batch_repository,
        report_repository=report_repository,
        demo_data_service=demo_data_service,
        ai_engine=ai_engine,
    )
