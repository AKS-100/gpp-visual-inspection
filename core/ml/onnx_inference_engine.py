"""
ONNXInferenceEngine — runs the trained model via ONNX Runtime.

Works on Python 3.14 (unlike tensorflow-cpu which requires <=3.12).
The .onnx model is converted once locally from the .keras file using
the convert_to_onnx.py script, then committed to the repository.
"""

import logging
from pathlib import Path

import numpy as np

from core.ml.inference_engine import PredictionResult

logger = logging.getLogger(__name__)


class ONNXInferenceEngine:
    """Implements the AIInferenceEngine protocol using ONNX Runtime."""

    def __init__(
        self,
        model_path: str,
        version_label: str,
        confidence_threshold: float = 0.5,
    ) -> None:
        self._model_path = model_path
        self._version_label = version_label
        self._confidence_threshold = confidence_threshold
        self._session = None
        logger.info("ONNXInferenceEngine registered for lazy loading: %s", version_label)

    @property
    def _ort_session(self):
        """Lazily load the ONNX Runtime session on first prediction."""
        if self._session is None:
            import onnxruntime as ort
            logger.info("Loading ONNX model from %s ...", self._model_path)
            self._session = ort.InferenceSession(
                self._model_path,
                providers=["CPUExecutionProvider"],
            )
            logger.info("ONNX model loaded. Input: %s", self._session.get_inputs()[0].shape)
        return self._session

    def predict(self, image_path: str) -> PredictionResult:
        """Run inference using ONNX Runtime."""
        from core.ml.preprocessing import load_and_preprocess_image

        preprocessed = load_and_preprocess_image(image_path)  # (1, 224, 224, 3) float32
        if preprocessed.dtype != np.float32:
            preprocessed = preprocessed.astype(np.float32)

        session = self._ort_session
        input_name = session.get_inputs()[0].name
        outputs = session.run(None, {input_name: preprocessed})

        # outputs[0] shape: (1, 2) — [prob_GOOD, prob_DEFECTIVE]
        probs = outputs[0][0]
        # label_encoder: {"GOOD": 0, "DEFECTIVE": 1}
        defective_probability = float(probs[1]) if len(probs) > 1 else float(probs[0])

        is_defective = defective_probability >= self._confidence_threshold
        confidence = defective_probability if is_defective else (1.0 - defective_probability)

        return PredictionResult(
            prediction="DEFECTIVE" if is_defective else "GOOD",
            confidence_score=round(confidence, 4),
            heatmap_path=None,
            defect_ids=[],
        )

    @property
    def model_version_label(self) -> str:
        return self._version_label
