"""
labels.py 
"""
import math
import re

UNCERTAINTY_THRESHOLD = 0.65   # max(prob) below this => "Uncertain"

UI_REAL = "Likely Real"
UI_FAKE = "Likely Misinformation"
UI_UNCERTAIN = "Uncertain"

_ALIASES = {
    "real": UI_REAL, "true": UI_REAL, "likely real": UI_REAL, "1": UI_REAL,
    "fake": UI_FAKE, "false": UI_FAKE, "misinformation": UI_FAKE,
    "likely misinformation": UI_FAKE, "likely fake": UI_FAKE, "0": UI_FAKE,
    "uncertain": UI_UNCERTAIN, "unknown": UI_UNCERTAIN,
}


def to_ui_label(label):
    """Map any backend / legacy label to a UI label (default: Uncertain)."""
    return _ALIASES.get(str(label).strip().lower(), UI_UNCERTAIN)


def verdict_from_probs(fake_prob, real_prob, threshold=UNCERTAINTY_THRESHOLD):
    """Return (ui_label, confidence) from the two model probabilities."""
    fake_prob, real_prob = float(fake_prob), float(real_prob)
    confidence = max(fake_prob, real_prob)
    if confidence < threshold:
        return UI_UNCERTAIN, confidence
    return (UI_REAL if real_prob >= fake_prob else UI_FAKE), confidence


def _num(v, default=None):
    try:
        f = float(v)
        return default if math.isnan(f) else f
    except (TypeError, ValueError):
        return default


def probs_for_display(prediction, confidence, prob_misinfo=None, prob_real=None):
    """
    Return (prob_misinfo, prob_real). Uses the real stored probabilities when
    available; otherwise reconstructs them from the label + confidence.
    """
    pm, pr = _num(prob_misinfo), _num(prob_real)
    if pm is not None and pr is not None:
        return pm, pr
    c = _num(confidence, 0.5)
    label = to_ui_label(prediction)
    if label == UI_FAKE:
        return c, 1 - c
    if label == UI_REAL:
        return 1 - c, c
    return 0.5, 0.5   # genuinely unknown (legacy rows only)


def categorize(val):
    """Numeric (0-1) -> Low / Moderate / High."""
    v = _num(val)
    if v is None:
        return "Moderate"
    v = abs(v)
    return "Low" if v < 0.33 else ("Moderate" if v < 0.66 else "High")


def _label_for(score):
    return "High" if score > 0.66 else ("Moderate" if score > 0.33 else "Low")


# explanation segment name -> which numeric feature drives its bar
_SEGMENT_FEATURE = {
    "tone": "sentiment",
    "content": "subjectivity",
    "readability": "readability",
    "exclamation marks": "exclamation_ratio",
    "capitalization": "uppercase_ratio",
}
_SUMMARY_SCORE = {"CREDIBLE": 0.15, "CAUTION": 0.4, "MIXED": 0.6, "SUSPICIOUS": 0.85}


def parse_explanation(text, features=None):
    """
    Turn the backend explanation string into the list of
    {feature, score, label, text} items the UI cards render.

    Backend format (single line):
      "<summary> Tone: X. Content: Y. Readability: Z. Exclamation marks: W.
       Capitalization: V. [Analyzes STYLE only, not FACTS]"
    """
    if features is None:
        features = {}
    if not text or not isinstance(text, str) or len(text.strip()) < 5:
        return [{"feature": "Analysis", "score": 0.5, "label": "Mixed",
                 "text": "No explanation available"}]

    body = re.sub(r"\[[^\]]*\]", "", text).strip()          # drop "[Analyzes ...]"
    # split "<summary> Tone: ..." at the first known segment name
    m = re.search(r"\b(Tone|Content|Readability|Exclamation marks|Capitalization):", body)
    summary, rest = (body[:m.start()].strip(), body[m.start():]) if m else (body, "")

    items = []
    if summary:
        score = 0.5
        for key, val in _SUMMARY_SCORE.items():
            if key in summary.upper():
                score = val
        items.append({"feature": "Overall Assessment", "score": score,
                      "label": _label_for(score), "text": summary})

    for seg in re.split(r"(?<=\.)\s+(?=[A-Z][A-Za-z ]+:)", rest):
        if ":" not in seg:
            continue
        name, val = seg.split(":", 1)
        name, val = name.strip(), val.strip().rstrip(".")
        fkey = _SEGMENT_FEATURE.get(name.lower())
        fval = _num(features.get(fkey)) if fkey else None
        score = min(abs(fval), 1.0) if fval is not None else 0.5
        items.append({"feature": name, "score": round(score, 3),
                      "label": _label_for(score), "text": val})

    return items or [{"feature": "Assessment", "score": 0.5, "label": "Mixed",
                      "text": body[:200]}]
