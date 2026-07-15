"""
AI inference interface.

`inspection_service` depends only on `AIInferenceEngine`. Today that
resolves to `DummyInferenceEngine`; Phase 6/7 introduces
`TensorFlowInferenceEngine` implementing the same protocol, and
`inspection_service.py` does not change at all when that swap happens.
"""

import hashlib
from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class PredictionResult:
    """Result of running one image through an inference engine."""

    prediction: str  # "GOOD" or "DEFECTIVE"
    confidence_score: float  # 0.0-1.0
    heatmap_path: str | None  # Grad-CAM overlay path, once Phase 7 implements it
    defect_ids: list[int]  # empty when prediction == "GOOD"


class AIInferenceEngine(Protocol):
    """Contract every inference engine (stub or real model) must satisfy."""

    def predict(self, image_path: str) -> PredictionResult:
        """Run inference on the image at `image_path` and return a PredictionResult."""
        ...

    @property
    def model_version_label(self) -> str:
        """
        A string identifying this engine's exact model + version, stored
        verbatim on every inspection row as `model_version_snapshot` so
        history stays meaningful even if the model registry changes later.
        """
        ...


class DummyInferenceEngine:
    """
    Placeholder inference engine used until Phase 6/7 trains a real model.

    Deterministic rather than randomized: the outcome is derived from a
    hash of the image path, so the same image always produces the same
    result. This makes the inspection workflow demonstrable and testable
    today without a trained model, while behaving like a real classifier
    (stable output per input) rather than a coin flip.
    """

    def __init__(self, defect_ids_pool: list[int] | None = None) -> None:
        # A small pool of plausible defect ids to attach to a "DEFECTIVE"
        # result. Passed in by the caller (inspection_service already
        # knows the real defect_type ids from defect_repository) rather
        # than hardcoded here, so this stub has zero knowledge of the
        # database schema.
        self._defect_ids_pool = defect_ids_pool or []

    def predict(self, image_path: str) -> PredictionResult:
        digest = hashlib.sha256(image_path.encode("utf-8")).hexdigest()
        digest_value = int(digest[:8], 16)

        is_defective = (digest_value % 10) < 3  # ~30% defective rate, plausible for a demo
        confidence = 0.75 + (digest_value % 2500) / 10000  # 0.75-1.00

        defect_ids = []
        if is_defective and self._defect_ids_pool:
            defect_ids = [self._defect_ids_pool[digest_value % len(self._defect_ids_pool)]]

        return PredictionResult(
            prediction="DEFECTIVE" if is_defective else "GOOD",
            confidence_score=round(confidence, 4),
            heatmap_path=None,  # Grad-CAM not implemented until Phase 7
            defect_ids=defect_ids,
        )

    @property
    def model_version_label(self) -> str:
        return "dummy-inference-engine:0.0.0-stub"
