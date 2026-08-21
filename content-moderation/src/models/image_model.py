import numpy as np
from PIL import Image
import tensorflow as tf
import io

MODEL_PATH = "models/nsfw_mobilenet.h5"
IMAGE_SIZE = (224, 224)

# Model's output classes, in the order the model was trained to output them
CLASS_NAMES = ["drawings", "hentai", "neutral", "porn", "sexy"]
UNSAFE_CLASSES = {"hentai", "porn", "sexy"}

_model = None

def load_model():
    global _model
    if _model is None:
        _model = tf.keras.models.load_model(MODEL_PATH)
    return _model

def preprocess(image_bytes: bytes) -> np.ndarray:
    img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    img = img.resize(IMAGE_SIZE)
    arr = np.array(img) / 255.0
    return np.expand_dims(arr, axis=0)

def predict(image_bytes: bytes) -> dict:
    model = load_model()
    x = preprocess(image_bytes)
    preds = model.predict(x, verbose=0)[0]

    scores = {name: float(score) for name, score in zip(CLASS_NAMES, preds)}
    unsafe_score = sum(scores[c] for c in UNSAFE_CLASSES)

    return {
        "scores": scores,
        "unsafe_score": unsafe_score,
    }