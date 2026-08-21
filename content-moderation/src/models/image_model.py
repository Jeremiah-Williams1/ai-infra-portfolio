import numpy as np
from PIL import Image
import io
import opennsfw2 as n2

_model = None

def load_model():
    global _model
    if _model is None:
        # Downloads weights to ~/.opennsfw2/weights/ on first call, reused after
        _model = n2.make_open_nsfw_model()
    return _model

def predict(image_bytes: bytes) -> dict:
    model = load_model()

    pil_image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    preprocessed = n2.preprocess_image(pil_image, n2.Preprocessing.YAHOO)
    x = np.expand_dims(preprocessed, axis=0)

    predictions = model.predict(x, verbose=0)
    non_nsfw_prob, nsfw_prob = predictions[0]

    return {
        "scores": {"safe": float(non_nsfw_prob), "nsfw": float(nsfw_prob)},
        "unsafe_score": float(nsfw_prob),
    }