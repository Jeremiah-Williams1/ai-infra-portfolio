from enum import Enum
from . import config


class Decision(str, Enum):
    PASS = "pass"
    FLAG = "flag"
    BLOCK = "block"


def decide_image(unsafe_score: float) -> Decision:
    if unsafe_score >= config.IMAGE_UNSAFE_THRESHOLD:
        return Decision.BLOCK
    if unsafe_score >= config.IMAGE_REVIEW_THRESHOLD:
        return Decision.FLAG
    return Decision.PASS


def decide_text(toxic_score: float) -> Decision:
    if toxic_score >= config.TEXT_TOXIC_THRESHOLD:
        return Decision.BLOCK
    return Decision.PASS


def combine(image_decision: Decision, text_decision: Decision) -> Decision:
    """Worst-of-both-wins: if either side says block, block. Else if either flags, flag."""
    severity = {Decision.PASS: 0, Decision.FLAG: 1, Decision.BLOCK: 2}
    worst = max(image_decision, text_decision, key=lambda d: severity[d])
    return worst


def evaluate(image_result: dict, text_result: dict | None = None) -> dict:
    image_decision = decide_image(image_result["unsafe_score"])

    if text_result is not None:
        text_decision = decide_text(text_result["toxic_score"])
        final = combine(image_decision, text_decision)
    else:
        text_decision = None
        final = image_decision

    return {
        "final_decision": final.value,
        "image_decision": image_decision.value,
        "text_decision": text_decision.value if text_decision else None,
        "image_scores": image_result["scores"],
        "text_scores": text_result["scores"] if text_result else None,
    }