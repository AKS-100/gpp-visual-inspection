"""Data augmentation — applied only to the training split, never validation/test."""


def build_augmentation_pipeline():
    """
    Returns a Keras Sequential of augmentation layers appropriate for
    industrial parts photography: mild geometric jitter and lighting
    variation, deliberately conservative (defects like scratches/cracks
    must survive augmentation recognizably — aggressive distortion would
    teach the model to ignore exactly the features that matter).
    """
    from tensorflow.keras import layers, Sequential

    return Sequential(
        [
            layers.RandomFlip("horizontal_and_vertical"),
            layers.RandomRotation(0.15),       # wider: ±54° instead of ±29°
            layers.RandomZoom(0.2),            # wider: ±20% instead of ±10%
            layers.RandomContrast(0.2),        # wider: ±20% instead of ±10%
            layers.RandomBrightness(0.2),      # wider: ±20% instead of ±10%
            layers.RandomTranslation(0.1, 0.1), # new: small shifts up to 10%
        ],
        name="augmentation_pipeline",
    )
