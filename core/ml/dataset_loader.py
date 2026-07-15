"""
Dataset loader.

Discovers (image_path, label) pairs from a dataset root without assuming
a single fixed folder layout — different industrial datasets organize
their good/defective images differently, so discovery is delegated to an
"adapter" per dataset family. Adding a third dataset later means writing
one small adapter (or often reusing an existing one with new keywords),
not touching the training pipeline.

Labels are always normalized to "GOOD" / "DEFECTIVE" — this is what keeps
the rest of the pipeline (and TensorFlowInferenceEngine) dataset-agnostic.
"""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp"}
GOOD_LABEL = "GOOD"
DEFECTIVE_LABEL = "DEFECTIVE"


@dataclass(frozen=True)
class Sample:
    image_path: str
    label: str  # GOOD or DEFECTIVE
    source_dataset: str  # which dataset this sample came from, for logging/analysis


class DatasetAdapter(ABC):
    """Base class every dataset adapter implements. discover() does no I/O beyond globbing/listing."""

    def __init__(self, root: Path, dataset_name: str) -> None:
        self.root = Path(root)
        self.dataset_name = dataset_name

    @abstractmethod
    def discover(self) -> list[Sample]:
        raise NotImplementedError

    def _iter_images(self, directory: Path):
        for path in directory.rglob("*"):
            if path.suffix.lower() in IMAGE_EXTENSIONS:
                yield path


class MVTecStyleAdapter(DatasetAdapter):
    """
    Adapter for MVTec-AD-style datasets: root/{train,test}/<class_name>/*.png,
    where a "good" class folder is normal and every other class folder under
    test/ is a distinct defect type. Reusable for any MVTec AD category
    (screw, bottle, capsule, ...) without modification — only the root path
    changes.
    """

    def __init__(self, root: Path, dataset_name: str, good_dir_names: set[str] | None = None) -> None:
        super().__init__(root, dataset_name)
        self.good_dir_names = {name.lower() for name in (good_dir_names or {"good"})}

    def discover(self) -> list[Sample]:
        if not self.root.exists():
            logger.warning("Dataset root %s does not exist — skipping %s.", self.root, self.dataset_name)
            return []

        samples: list[Sample] = []
        for split_dir in self.root.iterdir():
            if not split_dir.is_dir() or split_dir.name.lower() == "ground_truth":
                continue
            for class_dir in split_dir.iterdir():
                if not class_dir.is_dir():
                    continue
                label = GOOD_LABEL if class_dir.name.lower() in self.good_dir_names else DEFECTIVE_LABEL
                for image_path in self._iter_images(class_dir):
                    samples.append(Sample(str(image_path), label, self.dataset_name))

        logger.info("%s: discovered %d samples from %s", self.dataset_name, len(samples), self.root)
        return samples


class KeywordLabeledDatasetAdapter(DatasetAdapter):
    """
    Adapter for datasets where every image sits under a folder whose name
    contains a recognizable keyword (e.g. Kaggle casting data's
    'ok_front' / 'def_front'). Matches case-insensitively against any
    parent directory name — works regardless of train/test/val nesting.
    """

    def __init__(self, root: Path, dataset_name: str, good_keywords: list[str], defect_keywords: list[str]) -> None:
        super().__init__(root, dataset_name)
        self.good_keywords = [k.lower() for k in good_keywords]
        self.defect_keywords = [k.lower() for k in defect_keywords]

    def discover(self) -> list[Sample]:
        if not self.root.exists():
            logger.warning("Dataset root %s does not exist — skipping %s.", self.root, self.dataset_name)
            return []

        samples: list[Sample] = []
        skipped = 0
        for image_path in self._iter_images(self.root):
            label = self._infer_label(image_path)
            if label is None:
                skipped += 1
                continue
            samples.append(Sample(str(image_path), label, self.dataset_name))

        logger.info(
            "%s: discovered %d samples from %s (%d files skipped, no keyword match)",
            self.dataset_name, len(samples), self.root, skipped,
        )
        return samples

    def _infer_label(self, image_path: Path) -> str | None:
        parent_names = [p.name.lower() for p in image_path.parents]
        for name in parent_names:
            if any(kw in name for kw in self.good_keywords):
                return GOOD_LABEL
            if any(kw in name for kw in self.defect_keywords):
                return DEFECTIVE_LABEL
        return None


# ---------------------------------------------------------------------------
# Registry — this is the part that grows when a new dataset is added.
# Adding dataset #3 is a 3-line entry here, not a new code path elsewhere.
# ---------------------------------------------------------------------------

def get_screw_adapter(root: Path) -> DatasetAdapter:
    return MVTecStyleAdapter(root, dataset_name="mvtec_screw", good_dir_names={"good"})


def get_casting_adapter(root: Path) -> DatasetAdapter:
    return KeywordLabeledDatasetAdapter(
        root, dataset_name="casting",
        good_keywords=["ok", "good"],   # matches "ok_front" (Kaggle) and "good" (renamed)
        defect_keywords=["def"],        # matches "def_front" (Kaggle) and "defective" (renamed)
    )


DATASET_REGISTRY = {
    "screw": get_screw_adapter,
    "casting": get_casting_adapter,
}


def load_dataset(name: str, root: Path) -> list[Sample]:
    """Load one registered dataset by name."""
    if name not in DATASET_REGISTRY:
        raise ValueError(f"Unknown dataset '{name}'. Registered datasets: {list(DATASET_REGISTRY)}")
    adapter = DATASET_REGISTRY[name](root)
    return adapter.discover()


def load_combined_datasets(
    dataset_roots: dict[str, Path],
    balance_datasets: bool = True,
    seed: int = 42,
) -> list[Sample]:
    """
    Load and merge multiple datasets.

    When balance_datasets=True (the default), the minority class within each
    label group is OVERSAMPLED (repeated) to match the size of the largest
    dataset for that label. This keeps all images from the large casting
    dataset AND gives the model equal exposure to screw-defect patterns
    through repeated (augmented) copies. Unlike downsampling, no data is
    discarded — augmentation applied during build_tf_dataset ensures each
    repeated copy is a genuinely different view of the source image.
    """
    import random

    rng = random.Random(seed)

    # Load all datasets separately so we can balance per-dataset per-label.
    per_dataset: dict[str, list[Sample]] = {}
    for name, root in dataset_roots.items():
        per_dataset[name] = load_dataset(name, root)

    if balance_datasets and len(per_dataset) > 1:
        # For each label, find the MAXIMUM count across all datasets —
        # minority datasets will be oversampled up to this target.
        label_max: dict[str, int] = {}
        for label in (GOOD_LABEL, DEFECTIVE_LABEL):
            counts = [
                sum(1 for s in samples if s.label == label)
                for samples in per_dataset.values()
                if any(s.label == label for s in samples)
            ]
            if counts:
                label_max[label] = max(counts)

        balanced: list[Sample] = []
        for name, samples in per_dataset.items():
            for label, target in label_max.items():
                label_samples = [s for s in samples if s.label == label]
                if not label_samples:
                    continue
                original_count = len(label_samples)
                if original_count < target:
                    # Oversample by repeating until we reach target count.
                    repeated: list[Sample] = []
                    while len(repeated) < target:
                        repeated.extend(label_samples)
                    label_samples = repeated[:target]
                    rng.shuffle(label_samples)
                    logger.info(
                        "%s: oversampled %s from %d -> %d "
                        "(each source image repeated ~%.0fx; augmentation provides variety).",
                        name, label, original_count, target, target / original_count,
                    )
                balanced.extend(label_samples)
        all_samples = balanced
    else:
        all_samples = [s for samples in per_dataset.values() for s in samples]

    good_count = sum(1 for s in all_samples if s.label == GOOD_LABEL)
    defective_count = len(all_samples) - good_count
    logger.info(
        "Combined dataset (balanced=%s): %d total (%d GOOD / %d DEFECTIVE) across %s",
        balance_datasets, len(all_samples), good_count, defective_count, list(dataset_roots),
    )
    return all_samples


def split_samples(
    samples: list[Sample], train_frac: float = 0.7, val_frac: float = 0.15, seed: int = 42
) -> tuple[list[Sample], list[Sample], list[Sample]]:
    """
    Stratified train/val/test split.

    Stratifies by (source_dataset, label) rather than just label so that each
    dataset's class distribution is preserved independently across splits.
    This prevents a scenario where all screw-defective images are assigned to
    the test set while only casting-defective images end up in training.
    """
    import random

    rng = random.Random(seed)

    # Group by (source_dataset, label) — ensures per-source proportional splits.
    by_group: dict[str, list[Sample]] = {}
    for s in samples:
        key = f"{s.source_dataset}::{s.label}"
        by_group.setdefault(key, []).append(s)

    train, val, test = [], [], []
    for group_samples in by_group.values():
        shuffled = group_samples[:]
        rng.shuffle(shuffled)
        n = len(shuffled)
        train_end = int(n * train_frac)
        val_end = train_end + int(n * val_frac)
        train.extend(shuffled[:train_end])
        val.extend(shuffled[train_end:val_end])
        test.extend(shuffled[val_end:])

    rng.shuffle(train)
    rng.shuffle(val)
    rng.shuffle(test)
    logger.info(
        "Split (per-source stratified): %d train / %d val / %d test",
        len(train), len(val), len(test),
    )
    return train, val, test


def build_tf_dataset(samples: list[Sample], batch_size: int = 32, shuffle: bool = False, augment: bool = False):
    """
    Build a tf.data.Dataset from Samples: decodes, resizes, and normalizes
    every image via preprocessing.load_and_preprocess_image_tf (the same
    function the inference engine uses), batches, and optionally augments
    and shuffles.
    """
    import tensorflow as tf

    from core.ml.augmentations import build_augmentation_pipeline
    from core.ml.preprocessing import load_and_preprocess_image_tf

    paths = [s.image_path for s in samples]
    labels = [0 if s.label == GOOD_LABEL else 1 for s in samples]

    ds = tf.data.Dataset.from_tensor_slices((paths, labels))

    if shuffle:
        ds = ds.shuffle(buffer_size=len(paths), seed=42, reshuffle_each_iteration=True)

    def _load(path, label):
        image = load_and_preprocess_image_tf(path)
        return image, label

    ds = ds.map(_load, num_parallel_calls=tf.data.AUTOTUNE)

    if augment:
        augmentation = build_augmentation_pipeline()
        ds = ds.map(lambda x, y: (augmentation(x, training=True), y), num_parallel_calls=tf.data.AUTOTUNE)

    return ds.batch(batch_size).prefetch(tf.data.AUTOTUNE)
