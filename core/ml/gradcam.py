"""
Grad-CAM — visual explanation overlay for a single prediction.

Isolated in its own module specifically so that a Grad-CAM failure (a
changed layer name after a model update, a malformed image, whatever)
never takes down the actual prediction. tensorflow_inference_engine.py
calls this wrapped in a try/except and proceeds with heatmap_path=None
on any error — inference must never depend on explainability succeeding.
"""

import logging
from pathlib import Path

import numpy as np

logger = logging.getLogger(__name__)

DEFAULT_LAST_CONV_LAYER = "top_conv"  # EfficientNetB0's final conv layer name


def generate_gradcam_overlay(
    model,
    preprocessed_image: np.ndarray,
    original_image: np.ndarray,
    output_path: Path,
    last_conv_layer_name: str = DEFAULT_LAST_CONV_LAYER,
) -> str | None:
    """
    Generate a Grad-CAM heatmap overlaid on the original image and save it.

    Returns the output path as a string on success, or None on any
    failure (logged, never raised — see module docstring).
    """
    try:
        import cv2
        import tensorflow as tf

        base_model = _find_base_model(model)
        conv_layer = base_model.get_layer(last_conv_layer_name)

        grad_model = tf.keras.models.Model(
            inputs=base_model.inputs, outputs=[conv_layer.output, base_model.output]
        )

        batch = np.expand_dims(preprocessed_image, axis=0)

        with tf.GradientTape() as tape:
            conv_output, predictions = grad_model(batch)
            loss = predictions[:, 0]

        grads = tape.gradient(loss, conv_output)
        pooled_grads = tf.reduce_mean(grads, axis=(0, 1, 2))

        conv_output = conv_output[0]
        heatmap = conv_output @ pooled_grads[..., tf.newaxis]
        heatmap = tf.squeeze(heatmap)
        heatmap = tf.maximum(heatmap, 0) / (tf.reduce_max(heatmap) + 1e-8)
        heatmap = heatmap.numpy()

        heatmap_resized = cv2.resize(heatmap, (original_image.shape[1], original_image.shape[0]))
        heatmap_colored = cv2.applyColorMap(np.uint8(255 * heatmap_resized), cv2.COLORMAP_JET)

        overlay = cv2.addWeighted(original_image.astype(np.uint8), 0.6, heatmap_colored, 0.4, 0)

        output_path.parent.mkdir(parents=True, exist_ok=True)
        cv2.imwrite(str(output_path), overlay)
        return str(output_path)

    except Exception:
        logger.exception("Grad-CAM generation failed — continuing without a heatmap.")
        return None


def _find_base_model(model):
    """
    The EfficientNetB0 base is a nested sub-model inside our classifier
    (see trainer.build_model) — Grad-CAM needs to reach into it directly
    to access its conv layers, not the outer wrapper model.
    """
    for layer in model.layers:
        if "efficientnet" in layer.name.lower():
            return layer
    raise ValueError("Could not locate the EfficientNetB0 base model inside the loaded model.")
