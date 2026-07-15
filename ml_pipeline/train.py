"""
Training entrypoint. Run locally where the datasets actually exist:

    python ml_pipeline/train.py --datasets screw casting --epochs 20 --fine-tune-epochs 10

This script only orchestrates calls into core/ml/*; it contains no model
or data logic itself; import it into the running Streamlit app.
"""

import argparse
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)

DATASET_ROOTS = {
    "screw": Path("data/screw_dataset"),
    "casting": Path("data/casting_dataset"),
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train the industrial defect classifier.")
    parser.add_argument("--datasets", nargs="+", default=["screw", "casting"], choices=list(DATASET_ROOTS))
    parser.add_argument("--epochs", type=int, default=20, help="Frozen-base training epochs.")
    parser.add_argument("--fine-tune-epochs", type=int, default=10)
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument("--unfreeze-last-n-layers", type=int, default=30)
    parser.add_argument("--output-model", default="models/industrial_quality_classifier.keras")
    parser.add_argument("--seed", type=int, default=42)
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    from core.ml.dataset_loader import build_tf_dataset, load_combined_datasets, split_samples
    from core.ml.evaluate import run_full_evaluation
    from core.ml.trainer import Trainer
    from core.ml.utils import compute_class_weights, configure_mixed_precision, save_json, set_seed

    set_seed(args.seed)
    configure_mixed_precision()

    roots = {name: DATASET_ROOTS[name] for name in args.datasets}
    samples = load_combined_datasets(roots, balance_datasets=True, seed=args.seed)
    if not samples:
        logger.error("No samples discovered. Check that %s contain the expected folder structure.", roots)
        sys.exit(1)

    train_samples, val_samples, test_samples = split_samples(samples, seed=args.seed)

    class_weight = compute_class_weights([0 if s.label == "GOOD" else 1 for s in train_samples])

    train_ds = build_tf_dataset(train_samples, batch_size=args.batch_size, shuffle=True, augment=True)
    val_ds = build_tf_dataset(val_samples, batch_size=args.batch_size, shuffle=False, augment=False)
    test_ds = build_tf_dataset(test_samples, batch_size=args.batch_size, shuffle=False, augment=False)

    trainer = Trainer()
    trainer.build_model()
    trainer.compile_model()

    logger.info("=== Phase 1: training classification head (frozen base) ===")
    trainer.train(train_ds, val_ds, epochs=args.epochs, class_weight=class_weight)

    logger.info("=== Phase 2: fine-tuning top layers ===")
    trainer.fine_tune(
        train_ds, val_ds, epochs=args.fine_tune_epochs,
        unfreeze_last_n_layers=args.unfreeze_last_n_layers, class_weight=class_weight,
    )

    output_path = Path(args.output_model)
    trainer.save_model(output_path)
    trainer.save_history(Path("models/training_history.json"))
    save_json({"GOOD": 0, "DEFECTIVE": 1}, Path("models/label_encoder.json"))

    logger.info("=== Evaluating on held-out test set ===")
    import numpy as np

    y_true, y_pred_proba = [], []
    for images, labels in test_ds:
        preds = trainer.model.predict(images, verbose=0).flatten()
        y_true.extend(labels.numpy().tolist())
        y_pred_proba.extend(preds.tolist())

    metrics = run_full_evaluation(np.array(y_true), np.array(y_pred_proba), Path("artifacts"))
    save_json(metrics, Path("artifacts/evaluation_metrics.json"))

    logger.info("Training complete. Model: %s | Metrics: %s", output_path, metrics)


if __name__ == "__main__":
    main()
