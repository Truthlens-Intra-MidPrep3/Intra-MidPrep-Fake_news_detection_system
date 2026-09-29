"""
TEXT HIGHLIGHTS - which parts of THIS article actually mattered.

"""

import re
import numpy as np

MAX_OCCLUSION_SENTENCES = 14     # each one costs a DistilBERT forward pass
TOP_SEMANTIC = 2                 # how many model-relevant passages to show
MIN_SEMANTIC_DELTA = 0.01        # ignore changes smaller than 1 % probability


def split_sentence_spans(text):
    """[(start, end)] of every sentence in the original text."""
    spans = []
    for m in re.finditer(r"[^.!?\n]+(?:[.!?]+|\n|$)", text):
        seg = m.group(0)
        stripped = seg.strip()
        if len(stripped) < 15:
            continue
        lead = len(seg) - len(seg.lstrip())
        spans.append((m.start() + lead, m.start() + lead + len(stripped)))
    return spans


def _real_prob(text, model):
    from feature_extraction import extract_features_single
    from preprocessing import normalize_text
    feats = extract_features_single(normalize_text(text)).reshape(1, -1)
    return float(model.predict_proba(feats)[0][1])


def semantic_highlights(text, model):
    spans = split_sentence_spans(text)
    if len(spans) < 2:
        return []                      # nothing to leave out
    if len(spans) > MAX_OCCLUSION_SENTENCES:
        # keep runtime bounded: evenly sample sentences
        idx = np.linspace(0, len(spans) - 1, MAX_OCCLUSION_SENTENCES).astype(int)
        spans_eval = [spans[i] for i in sorted(set(idx))]
    else:
        spans_eval = spans

    base = _real_prob(text, model)
    scored = []
    for s, e in spans_eval:
        without = (text[:s] + " " + text[e:]).strip()
        if len(without) < 10:
            continue
        delta = _real_prob(without, model) - base       # >0: sentence pushed toward FAKE
        scored.append((abs(delta), delta, s, e))

    scored.sort(reverse=True)
    out = []
    for mag, delta, s, e in scored[:TOP_SEMANTIC]:
        if mag < MIN_SEMANTIC_DELTA:
            continue
        direction = "misinformation" if delta > 0 else "real"
        out.append({"start": s, "end": e, "type": "semantic",
                    "reason": f"Removing this passage shifts the model by {mag*100:.1f}% "
                              f"(it pushes toward {direction})"})
    return out


def linguistic_highlights(text):
    from explanation_user_improved import _COMMON_ACRONYMS, _SHOUT_SHORT
    from textblob import TextBlob
    out = []

    # ALL-CAPS shouting words
    for m in re.finditer(r"\b[A-Z][A-Z0-9']+\b", text):
        w = m.group(0)
        if w in _COMMON_ACRONYMS:
            continue
        if len(w) >= 4 or w in _SHOUT_SHORT:
            out.append({"start": m.start(), "end": m.end(), "type": "linguistic",
                        "reason": "ALL-CAPS emphasis"})

    # Exclamation marks (highlight the sentence)
    for s, e in split_sentence_spans(text):
        sent = text[s:e]
        if "!" in sent:
            out.append({"start": s, "end": e, "type": "linguistic",
                        "reason": "Exclamation / sensational punctuation"})
            continue
        try:
            b = TextBlob(sent).sentiment
        except Exception:
            continue
        if abs(b.polarity) >= 0.5 or b.subjectivity >= 0.75:
            why = "Strongly emotional wording" if abs(b.polarity) >= 0.5 else "Highly opinionated wording"
            out.append({"start": s, "end": e, "type": "linguistic", "reason": why})
    return out


def compute_highlights(text, model_path=None):
    """Main entry point. Never raises - highlights are an optional extra."""
    highlights = []
    try:
        from model_prediction import load_model, DEFAULT_MODEL_PATH
        model = load_model(model_path or DEFAULT_MODEL_PATH)
        highlights += semantic_highlights(text, model)
    except Exception as e:                       # noqa: BLE001
        print(f"   Warning: model-relevant passages unavailable: {e}")
    try:
        highlights += linguistic_highlights(text)
    except Exception as e:                       # noqa: BLE001
        print(f"   Warning: linguistic highlights unavailable: {e}")
    return sorted(highlights, key=lambda h: h["start"])
