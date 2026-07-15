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
    Resize + apply EfficientNet's expected preprocessing to a single image
    array (H, W, 3), uint8 or float. Returns a float32 array ready for the
    model, still shaped (H, W, 3) — batching is the caller's responsibility.
    """
    import tensorflow as tf
    from tensorflow.keras.applications.efficientnet import preprocess_input

    image = tf.image.resize(image_array, IMAGE_SIZE)
    image = preprocess_input(image)
    return image.numpy() if hasattr(image, "numpy") else image


def load_and_preprocess_image(image_path: str) -> np.ndarray:
    """Load an image from disk and preprocess it identically to the training pipeline."""
    import tensorflow as tf

    raw = tf.io.read_file(image_path)
    image = tf.io.decode_image(raw, channels=3, expand_animations=False)
    image = tf.cast(image, tf.float32)
    return preprocess_image_array(image.numpy())


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
