"""
Trainer — builds, trains, fine-tunes, and saves the EfficientNetB0
classifier. Separated from dataset_loader (data) and predictor (serving)
so each module has exactly one job.

Why EfficientNetB0 over alternatives (see docs/ML_Pipeline.md for the
full comparison): best accuracy-per-parameter for a binary industrial
defect classifier deployed on commodity hardware, small enough (5.3M
params) to fine-tune well on a few thousand images without overfitting
as badly as ResNet50, and its compound-scaling design generalizes better
than a from-scratch CNN would with this little data.
"""

import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class Trainer:
    """Owns the model lifecycle: build -> train (frozen base) -> fine-tune (unfrozen top) -> save."""

    def __init__(self, image_size: tuple[int, int] = (224, 224), artifacts_dir: Path = Path("artifacts")) -> None:
        self.image_size = image_size
        self.artifacts_dir = artifacts_dir
        self.model = None
        self.history: dict = {}

    def build_model(self, dropout: float = 0.3):
        """Build EfficientNetB0 with a frozen base and a fresh binary classification head."""
        from tensorflow.keras import layers, Model
        from tensorflow.keras.applications import EfficientNetB0

        base_model = EfficientNetB0(
            include_top=False, weights="imagenet", input_shape=(*self.image_size, 3), pooling="avg"
        )
        base_model.trainable = False  # frozen for initial transfer-learning phase

        inputs = layers.Input(shape=(*self.image_size, 3))
        x = base_model(inputs, training=False)
        x = layers.Dropout(dropout)(x)
        outputs = layers.Dense(1, activation="sigmoid", dtype="float32")(x)  # float32 head even under mixed precision

        self.model = Model(inputs, outputs, name="efficientnetb0_defect_classifier")
        self._base_model = base_model
        logger.info("Built EfficientNetB0 model: %d total params, base frozen.", self.model.count_params())
        return self.model

    def compile_model(self, learning_rate: float = 1e-3) -> None:
        from tensorflow.keras.metrics import AUC, Precision, Recall
        from tensorflow.keras.optimizers import Adam

        self.model.compile(
            optimizer=Adam(learning_rate=learning_rate),
            loss="binary_crossentropy",
            metrics=["accuracy", AUC(name="auc"), Precision(name="precision"), Recall(name="recall")],
        )

    def get_callbacks(self, checkpoint_path: Path, log_dir: Path) -> list:
        from tensorflow.keras.callbacks import (
            EarlyStopping, ModelCheckpoint, ReduceLROnPlateau, TensorBoard,
        )

        checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
        log_dir.mkdir(parents=True, exist_ok=True)

        return [
            EarlyStopping(monitor="val_auc", mode="max", patience=5, restore_best_weights=True),
            ReduceLROnPlateau(monitor="val_loss", factor=0.5, patience=3, min_lr=1e-6),
            ModelCheckpoint(str(checkpoint_path), monitor="val_auc", mode="max", save_best_only=True),
            TensorBoard(log_dir=str(log_dir)),
        ]

    def train(
        self,
        train_ds,
        val_ds,
        epochs: int = 20,
        class_weight: dict | None = None,
        checkpoint_path: Path = Path("models/checkpoints/best_frozen.keras"),
        log_dir: Path = Path("artifacts/tensorboard/frozen"),
    ):
        """Phase 1: train the classification head with the EfficientNetB0 base frozen."""
        history = self.model.fit(
            train_ds,
            validation_data=val_ds,
            epochs=epochs,
            class_weight=class_weight,
            callbacks=self.get_callbacks(checkpoint_path, log_dir),
        )
        self.history["frozen_phase"] = history.history
        return history

    def fine_tune(
        self,
        train_ds,
        val_ds,
        epochs: int = 10,
        unfreeze_last_n_layers: int = 30,
        learning_rate: float = 1e-5,
        class_weight: dict | None = None,
        checkpoint_path: Path = Path("models/checkpoints/best_finetuned.keras"),
        log_dir: Path = Path("artifacts/tensorboard/finetuned"),
    ):
        """
        Phase 2: unfreeze the top N layers of the base model and continue
        training at a much lower learning rate. Only run this after the
        frozen-head phase has converged — fine-tuning from random head
        weights destroys the pretrained features.
        """
        self._base_model.trainable = True
        for layer in self._base_model.layers[:-unfreeze_last_n_layers]:
            layer.trainable = False

        self.compile_model(learning_rate=learning_rate)
        logger.info("Fine-tuning: unfroze last %d layers of the base model.", unfreeze_last_n_layers)

        history = self.model.fit(
            train_ds,
            validation_data=val_ds,
            epochs=epochs,
            class_weight=class_weight,
            callbacks=self.get_callbacks(checkpoint_path, log_dir),
        )
        self.history["finetune_phase"] = history.history
        return history

    def save_model(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        self.model.save(path)
        logger.info("Model saved to %s", path)

    def save_history(self, path: Path) -> None:
        from core.ml.utils import save_json

        save_json(self.history, path)
