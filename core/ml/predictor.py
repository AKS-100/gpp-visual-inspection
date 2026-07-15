"""
Predictor — thin wrapper around a loaded Keras model. Deliberately knows
nothing about AIInferenceEngine, PredictionResult, or the database; it
only turns a preprocessed image into a raw probability. This separation
is what let tensorflow_inference_engine.py be a thin adapter instead of
mixing model-loading concerns with the app's domain interface.
"""

import logging
import numpy as np

logger = logging.getLogger(__name__)


class Predictor:
    """Loads a saved .keras model once and exposes a single predict_proba method."""

    def __init__(self, model_path: str) -> None:
        import tensorflow as tf

        self.model = tf.keras.models.load_model(model_path)
        logger.info("Loaded model from %s", model_path)

    def predict_proba(self, preprocessed_image: np.ndarray) -> float:
        """
        Args:
            preprocessed_image: (H, W, 3) array, already resized/normalized
                by core.ml.preprocessing — this method does no preprocessing.

        Returns:
            Probability of the DEFECTIVE class (sigmoid output, 0.0-1.0).
        """
        batch = np.expand_dims(preprocessed_image, axis=0)
        probability = float(self.model.predict(batch, verbose=0)[0][0])
        return probability
