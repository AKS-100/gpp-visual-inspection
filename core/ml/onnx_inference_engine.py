"""
ONNXInferenceEngine — runs the trained EfficientNetB0 model via ONNX Runtime.

Works on Python 3.14 (unlike tensorflow-cpu which requires <=3.12).
The .onnx model is converted from the .keras file using tf2onnx and committed
to the repository so Streamlit Cloud can load it without TensorFlow.

The conversion produces 3 graph inputs:
  1. input_layer_2:0          — image tensor (batch, 224, 224, 3)
  2. normalization_1/Sub/y:0  — normalization mean  (1, 1, 1, 3)  [constant]
  3. normalization_1/Sqrt/x:0 — normalization variance (1, 1, 1, 3) [constant]

The mean and variance are the standard ImageNet stats used during training
and are hardcoded here so no Keras/TF dependency is needed at inference time.
"""

import logging
from pathlib import Path

import numpy as np

from core.ml.inference_engine import PredictionResult

logger = logging.getLogger(__name__)

# ImageNet normalisation constants — extracted from the Keras Normalization layer
_NORM_MEAN = np.array([[[[0.485, 0.456, 0.406]]]], dtype=np.float32)   # (1,1,1,3)
_NORM_VAR  = np.array([[[[0.229, 0.224, 0.225]]]], dtype=np.float32)   # (1,1,1,3)


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
        logger.info("ONNXInferenceEngine registered (lazy load): %s", version_label)

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
            inputs = self._session.get_inputs()
            logger.info(
                "ONNX model loaded. %d input(s): %s",
                len(inputs),
                [i.name for i in inputs],
            )
        return self._session

    def predict(self, image_path: str) -> PredictionResult:
        """Run inference using ONNX Runtime."""
        from core.ml.preprocessing import load_and_preprocess_image

        preprocessed = load_and_preprocess_image(image_path)  # (1, 224, 224, 3)
        if preprocessed.dtype != np.float32:
            preprocessed = preprocessed.astype(np.float32)

        session = self._ort_session
        input_names = [inp.name for inp in session.get_inputs()]

        # Build feed dict.
        # The converted model exposes the Normalization layer's constants as
        # graph inputs — pass the hardcoded ImageNet mean & variance.
        feed = {input_names[0]: preprocessed}
        if len(input_names) >= 2:
            feed[input_names[1]] = _NORM_MEAN   # Sub/y  — mean
        if len(input_names) >= 3:
            feed[input_names[2]] = _NORM_VAR    # Sqrt/x — variance

        outputs = session.run(None, feed)

        # Output shape is (batch, 1) — sigmoid probability of DEFECTIVE class
        raw_prob = float(outputs[0][0][0])
        defective_probability = raw_prob

        is_defective = defective_probability >= self._confidence_threshold
        confidence = defective_probability if is_defective else (1.0 - defective_probability)

        logger.debug(
            "ONNX predict: path=%s  p_defective=%.4f  result=%s  conf=%.4f",
            image_path, defective_probability,
            "DEFECTIVE" if is_defective else "GOOD",
            confidence,
        )

        return PredictionResult(
            prediction="DEFECTIVE" if is_defective else "GOOD",
            confidence_score=round(confidence, 4),
            heatmap_path=None,
            defect_ids=[],
        )

    @property
    def model_version_label(self) -> str:
        return self._version_label
