"""
TensorFlowInferenceEngine — production inference engine implementing the
existing AIInferenceEngine protocol exactly. This is the only file that
needs to change in app/services.py to go from DummyInferenceEngine to a
real trained model; InspectionService is untouched.

Honest limitation, stated once here rather than hidden: PredictionResult
(defined in core/ml/inference_engine.py, unchanged by this phase) has no
field for "which dataset a sample resembles" or "which specific defect
subtype was detected" — the model trained here is a binary GOOD/DEFECTIVE
classifier, matching the interface's existing contract. Multi-class
defect-type classification (mapping to specific defect_types rows) is a
real capability gap, not a shortcut — it's documented as future work in
docs/ML_Pipeline.md rather than faked with a made-up mapping between
MVTec/casting defect categories and GPP's own defect taxonomy, which
would look like a feature but not correspond to anything the model
actually learned.
"""

import logging
from pathlib import Path

import numpy as np

from core.ml.inference_engine import PredictionResult
from core.ml.predictor import Predictor
from core.ml.preprocessing import load_and_preprocess_image

logger = logging.getLogger(__name__)


class TensorFlowInferenceEngine:
    """Implements the AIInferenceEngine protocol using a trained Keras model."""

    def __init__(
        self,
        model_path: str,
        version_label: str,
        confidence_threshold: float = 0.5,
        heatmap_output_dir: Path = Path("data/uploads/heatmaps"),
        enable_gradcam: bool = True,
    ) -> None:
        self._model_path = model_path
        self._version_label = version_label
        self._confidence_threshold = confidence_threshold
        self._heatmap_output_dir = heatmap_output_dir
        self._enable_gradcam = enable_gradcam
        self._predictor_instance = None
        logger.info("TensorFlowInferenceEngine registered for lazy loading: %s", version_label)

    @property
    def _predictor(self) -> Predictor:
        if self._predictor_instance is None:
            logger.info("Lazily loading TensorFlow model from %s...", self._model_path)
            self._predictor_instance = Predictor(self._model_path)
        return self._predictor_instance

    def predict(self, image_path: str) -> PredictionResult:
        preprocessed = load_and_preprocess_image(image_path)
        defective_probability = self._predictor.predict_proba(preprocessed)

        is_defective = defective_probability >= self._confidence_threshold
        confidence = defective_probability if is_defective else (1.0 - defective_probability)

        heatmap_path = self._try_generate_heatmap(image_path, preprocessed) if self._enable_gradcam else None

        # Binary classifier — no per-defect-type breakdown available yet, see module docstring.
        defect_ids: list[int] = []

        return PredictionResult(
            prediction="DEFECTIVE" if is_defective else "GOOD",
            confidence_score=round(float(confidence), 4),
            heatmap_path=heatmap_path,
            defect_ids=defect_ids,
        )

    def _try_generate_heatmap(self, image_path: str, preprocessed: np.ndarray) -> str | None:
        try:
            import cv2

            from core.ml.gradcam import generate_gradcam_overlay

            original = cv2.imread(image_path)
            if original is None:
                return None

            output_path = self._heatmap_output_dir / f"{Path(image_path).stem}_gradcam.jpg"
            return generate_gradcam_overlay(self._predictor.model, preprocessed, original, output_path)
        except Exception:
            logger.exception("Grad-CAM heatmap generation failed for %s — proceeding without it.", image_path)
            return None

    @property
    def model_version_label(self) -> str:
        return self._version_label
