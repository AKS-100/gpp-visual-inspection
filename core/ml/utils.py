"""Shared utilities for the ML pipeline — no training or inference logic lives here."""

import json
import logging
import random
from pathlib import Path
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)


def set_seed(seed: int = 42) -> None:
    """Seed Python, NumPy, and TensorFlow (if importable) for reproducible splits/augmentation."""
    random.seed(seed)
    np.random.seed(seed)
    try:
        import tensorflow as tf

        tf.random.set_seed(seed)
    except ImportError:
        logger.warning("TensorFlow not installed; only Python/NumPy seeds were set.")


def configure_mixed_precision() -> str:
    """
    Enable mixed_float16 if a GPU is available; falls back to float32 on CPU-only
    machines, where mixed precision gives no benefit and can even slow things down.
    Returns the policy name actually applied, for logging.
    """
    import tensorflow as tf

    gpus = tf.config.list_physical_devices("GPU")
    if gpus:
        tf.keras.mixed_precision.set_global_policy("mixed_float16")
        logger.info("Mixed precision enabled (mixed_float16) — %d GPU(s) detected.", len(gpus))
        return "mixed_float16"

    logger.info("No GPU detected — training will run in float32 on CPU.")
    return "float32"


def compute_class_weights(labels: list[int]) -> dict[int, float]:
    """
    Inverse-frequency class weights for imbalanced binary datasets (e.g. casting
    data typically skews toward defective samples). Passed to model.fit(class_weight=...).
    """
    labels_arr = np.array(labels)
    classes, counts = np.unique(labels_arr, return_counts=True)
    total = len(labels_arr)
    weights = {int(c): total / (len(classes) * count) for c, count in zip(classes, counts)}
    logger.info("Computed class weights: %s", weights)
    return weights


def ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def save_json(data: dict[str, Any], path: Path) -> None:
    ensure_dir(path.parent)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, default=str)
    logger.info("Saved %s", path)


def load_json(path: Path) -> dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)
