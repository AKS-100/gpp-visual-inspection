"""Evaluation — metrics and figures computed once after training, saved to artifacts/."""

import logging
from pathlib import Path

import numpy as np

logger = logging.getLogger(__name__)


def evaluate_predictions(y_true: np.ndarray, y_pred_proba: np.ndarray, threshold: float = 0.5) -> dict:
    """Compute accuracy, precision, recall, F1, and ROC-AUC for a binary classifier."""
    from sklearn.metrics import (
        accuracy_score, f1_score, precision_score, recall_score, roc_auc_score,
    )

    y_pred = (y_pred_proba >= threshold).astype(int)

    metrics = {
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "precision": float(precision_score(y_true, y_pred, zero_division=0)),
        "recall": float(recall_score(y_true, y_pred, zero_division=0)),
        "f1_score": float(f1_score(y_true, y_pred, zero_division=0)),
        "roc_auc": float(roc_auc_score(y_true, y_pred_proba)),
        "threshold": threshold,
    }
    logger.info("Evaluation metrics: %s", metrics)
    return metrics


def save_confusion_matrix(y_true: np.ndarray, y_pred_proba: np.ndarray, output_path: Path, threshold: float = 0.5) -> None:
    import matplotlib.pyplot as plt
    from sklearn.metrics import ConfusionMatrixDisplay, confusion_matrix

    y_pred = (y_pred_proba >= threshold).astype(int)
    matrix = confusion_matrix(y_true, y_pred)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(5, 5))
    ConfusionMatrixDisplay(matrix, display_labels=["GOOD", "DEFECTIVE"]).plot(ax=ax, cmap="Blues", colorbar=False)
    ax.set_title("Confusion Matrix")
    fig.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    logger.info("Saved confusion matrix to %s", output_path)


def save_roc_curve(y_true: np.ndarray, y_pred_proba: np.ndarray, output_path: Path) -> None:
    import matplotlib.pyplot as plt
    from sklearn.metrics import RocCurveDisplay

    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(5, 5))
    RocCurveDisplay.from_predictions(y_true, y_pred_proba, ax=ax)
    ax.set_title("ROC Curve")
    fig.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    logger.info("Saved ROC curve to %s", output_path)


def run_full_evaluation(y_true: np.ndarray, y_pred_proba: np.ndarray, artifacts_dir: Path) -> dict:
    """Compute metrics and save both figures in one call — what evaluate.py's CLI usage boils down to."""
    metrics = evaluate_predictions(y_true, y_pred_proba)
    save_confusion_matrix(y_true, y_pred_proba, artifacts_dir / "confusion_matrix.png")
    save_roc_curve(y_true, y_pred_proba, artifacts_dir / "roc_curve.png")
    return metrics
