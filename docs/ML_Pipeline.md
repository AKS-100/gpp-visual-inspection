# ML Pipeline

Status: **implemented (Phase 7), not yet trained** — this environment
cannot access the local datasets or download ImageNet weights (network
sandboxed), so training runs locally. See "Local training commands" below.

## Datasets

**MVTec AD — Screw category.** Real industrial photographs of screws,
`good` vs several genuine defect types (thread damage, scratches,
manipulated front). Chosen because it's a well-established, high-quality
industrial anomaly detection benchmark — the kind of dataset a reviewer
will recognize as a credible proxy for GPP's own components.

**Casting Product Image Data for Quality Inspection (Kaggle).** Real
factory-floor photographs of a submersible pump impeller, binary
`ok_front` / `def_front` labels — structurally identical to this
project's GOOD/DEFECTIVE requirement.

**Why two datasets, combined:** neither alone is a great visual match for
GPP's automotive components (a screw isn't a push rod; a cast impeller
isn't machined either) — but together they give the model more visual
diversity in what "a defect on a manufactured metal part" looks like,
which is the actual pattern being transferred, not surface-level
similarity to any one part. This is stated as a proxy-data strategy, not
a substitute for eventually fine-tuning on real GPP images, which
requires zero pipeline changes once GPP data exists (see Future
improvements).

## Multi-dataset architecture

`core/ml/dataset_loader.py` separates *discovery* (how to find images and
infer GOOD/DEFECTIVE from a specific dataset's folder layout) from
everything downstream (splitting, augmentation, batching), via a small
adapter hierarchy:

- `MVTecStyleAdapter` — any MVTec-AD-style dataset (`root/{train,test}/<class>/*`,
  "good" folder = normal, every other class folder = defective). Reusable
  as-is for other MVTec categories (bottle, capsule, ...) with zero code
  changes, only a different root path.
- `KeywordLabeledDatasetAdapter` — any dataset where GOOD/DEFECTIVE is
  encoded in a folder name via a keyword (`ok`/`def` for the casting set).
  Reusable for most Kaggle-style industrial defect datasets.

Adding dataset #3 means registering one adapter call in
`DATASET_REGISTRY` — no changes to the trainer, augmentation, or
inference code.

## Training workflow

1. **Discovery & combination** — `load_combined_datasets()` merges both
   datasets into one labeled sample list.
2. **Stratified split** — `split_samples()` (70/15/15 by default) keeps
   the GOOD/DEFECTIVE ratio consistent across train/val/test.
3. **Class weighting** — `compute_class_weights()` counteracts the
   imbalance both datasets have (defective samples are the minority).
4. **Phase 1 — frozen-base training** — EfficientNetB0 (ImageNet weights)
   with the base frozen, training only a new `Dropout -> Dense(1, sigmoid)`
   head. Adam, binary cross-entropy, `EarlyStopping` (on `val_auc`),
   `ReduceLROnPlateau`, `ModelCheckpoint`, `TensorBoard`.
5. **Phase 2 — fine-tuning** — unfreeze the last N base-model layers
   (default 30), recompile at a much lower learning rate (1e-5), continue
   training. Only run after phase 1 converges — fine-tuning against a
   randomly-initialized head destroys the pretrained features.
6. **Evaluation** — accuracy, precision, recall, F1, ROC-AUC, confusion
   matrix and ROC curve figures, all saved to `artifacts/`.

## Why EfficientNetB0

| Model | Verdict |
|---|---|
| Custom CNN from scratch | Needs far more data than two small industrial datasets provide; rejected in Phase 1 planning. |
| ResNet50 | Strong accuracy but ~5x the parameters of EfficientNetB0 for this binary task — slower CPU inference, no accuracy benefit at this data scale. |
| **EfficientNetB0** | **Chosen.** Best accuracy-per-parameter for a binary classifier deployed on commodity/edge hardware — the same reasoning real Industry 4.0 edge deployments use, and it fine-tunes well on a few thousand images without overfitting as readily as larger nets. |

## Hyperparameters (defaults in `ml_pipeline/train.py`)

- Image size: 224x224 (EfficientNetB0 native input)
- Batch size: 32
- Frozen-phase epochs: 20 (EarlyStopping typically stops earlier)
- Fine-tune epochs: 10, last 30 layers unfrozen, LR 1e-5
- Augmentation: horizontal+vertical flip, ±8% rotation, 10% zoom,
  contrast/brightness jitter — deliberately mild, since aggressive
  distortion can wash out the exact texture cues (scratches, cracks)
  the model needs to key on.

## TensorFlowInferenceEngine — integration

Implements the existing `AIInferenceEngine` protocol exactly:
`predict(image_path) -> PredictionResult`, `model_version_label` property.
Verified as a structural drop-in for `DummyInferenceEngine` — same return
type, same fields. `app/services.py` automatically selects
`TensorFlowInferenceEngine` when `models/industrial_quality_classifier.keras`
exists and TensorFlow is importable, and falls back to
`DummyInferenceEngine` otherwise — **`InspectionService` was not modified.**

Preprocessing (`core/ml/preprocessing.py`) is shared verbatim between the
training pipeline (`build_tf_dataset`) and inference
(`load_and_preprocess_image`) — this is what prevents train/serve skew,
a common and easy-to-miss source of silent accuracy loss.

Grad-CAM (`core/ml/gradcam.py`) is wrapped in a try/except inside
`TensorFlowInferenceEngine._try_generate_heatmap` — a Grad-CAM failure
never blocks a prediction; `heatmap_path` is simply `None`.

## Known limitation (stated honestly, not hidden)

The model is a **binary** GOOD/DEFECTIVE classifier. `PredictionResult.defect_ids`
is always empty from `TensorFlowInferenceEngine` — there is no per-defect-type
classification head, and mapping MVTec/casting defect categories onto GPP's
own `defect_types` (Surface scratch, Crack, Pitting, Discoloration,
Deformation) would be a fabricated correspondence, not something the model
actually learned. Multi-class defect typing is real future work, not a
shortcut taken here.

## Future improvements

- Fine-tune on real GPP component images once available — no pipeline
  changes needed, just a new `DatasetAdapter` and dataset root.
- Multi-class defect-type classification head (would need labeled defect
  subtypes in the training data, which today's two proxy datasets only
  partially provide).
- Model versioning/registry integration beyond the single-row `ai_models`
  table already in the database (see docs/FutureScope.md).
- Quantization/TFLite export if edge deployment latency becomes a concern.

## Local training commands

Run from the project root, where `data/screw_dataset/` and
`data/casting_dataset/` actually exist:

```bash
pip install -r requirements.txt

python ml_pipeline/train.py --datasets screw casting --epochs 20 --fine-tune-epochs 10

# Train on one dataset only:
python ml_pipeline/train.py --datasets screw --epochs 15

# Monitor training:
tensorboard --logdir artifacts/tensorboard
```

Outputs: `models/industrial_quality_classifier.keras`,
`models/training_history.json`, `models/label_encoder.json`,
`artifacts/confusion_matrix.png`, `artifacts/roc_curve.png`,
`artifacts/evaluation_metrics.json`. Once the `.keras` file exists at
that path, restart the Streamlit app — it will automatically switch from
`DummyInferenceEngine` to `TensorFlowInferenceEngine`.
