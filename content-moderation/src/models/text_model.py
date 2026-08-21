import os
os.environ["CUDA_VISIBLE_DEVICES"] = ""  # hide GPU from torch entirely, must be set before torch import

from transformers import pipeline

MODEL_NAME = "unitary/toxic-bert"

_classifier = None

def load_model():
    global _classifier
    if _classifier is None:
        _classifier = pipeline(
            "text-classification",
            model=MODEL_NAME,
            device=-1,
            top_k=None,
        )
    return _classifier

def predict(text: str) -> dict:
    if not text or not text.strip():
        return {"scores": {}, "toxic_score": 0.0}

    classifier = load_model()
    results = classifier(text)[0]

    scores = {r["label"]: float(r["score"]) for r in results}
    toxic_score = scores.get("toxic", 0.0)

    return {
        "scores": scores,
        "toxic_score": toxic_score,
    }