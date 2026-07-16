"""
Image preprocessing — shared by the training pipeline and the inference
engine. This is deliberately the *only* place that resizes/normalizes an
image, because any mismatch between how training data and inference-time
images are preprocessed silently degrades model accuracy (train/serve
skew) in a way that's very easy to miss.
"""

import numpy as np

IMAGE_SIZE: tuple[int, int] = (224, 224)  # EfficientNetB0's native input size


def preprocess_image_array(image_array: np.ndarray) -> np.ndarray:
    """
    Resize a single image array (H, W, 3) for EfficientNetB0.

    IMPORTANT: EfficientNetB0 (TF 2.x, include_top=False) includes its own
    Rescaling(1/255) + Normalization layers INSIDE the model.
    The preprocess_input() call in the training pipeline is a NO-OP for this
    TF version — it returns x unchanged. So the model expects raw pixel values
    in the [0, 255] float32 range. DO NOT divide by 255 here.

    Returns float32 array shaped (H, W, 3) with values in [0, 255].
    """
    import cv2

    # Ensure uint8 for resize, then cast back to float32 in [0,255]
    if image_array.dtype != np.uint8:
        image_array = np.clip(image_array, 0, 255).astype(np.uint8)

    resized = cv2.resize(
        image_array,
        (IMAGE_SIZE[1], IMAGE_SIZE[0]),   # cv2 takes (width, height)
        interpolation=cv2.INTER_LINEAR,
    )
    return resized.astype(np.float32)     # [0, 255] float32 — model rescales internally


def load_and_preprocess_image(image_path: str) -> np.ndarray:
    """Load an image from disk and preprocess it identically to the training pipeline.

    Returns float32 array shaped (1, 224, 224, 3) with values in [0, 255].
    """
    import cv2

    bgr = cv2.imread(image_path)
    if bgr is None:
        raise ValueError(f"Could not read image at path: {image_path}")
    rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
    processed = preprocess_image_array(rgb)       # (224, 224, 3) float32 [0,255]
    return np.expand_dims(processed, axis=0)      # (1, 224, 224, 3)



def load_and_preprocess_image_tf(image_path):
    """
    tf.data-graph-mode variant of load_and_preprocess_image, for use inside
    a tf.data.Dataset.map() call during training (must stay in TF ops, not
    NumPy, to run efficiently in the data pipeline).
    """
    import tensorflow as tf
    from tensorflow.keras.applications.efficientnet import preprocess_input

    raw = tf.io.read_file(image_path)
    image = tf.io.decode_image(raw, channels=3, expand_animations=False)
    image.set_shape([None, None, 3])
    image = tf.image.resize(image, IMAGE_SIZE)
    image = tf.cast(image, tf.float32)
    image = preprocess_input(image)
    return image
