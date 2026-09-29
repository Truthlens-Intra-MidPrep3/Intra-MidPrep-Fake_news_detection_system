"""
backend_processor.py - Call the ML backend 

"""
import math
import shutil
import sys
import tempfile
import traceback
from pathlib import Path

import pandas as pd

from paths import find_backend_dir
from labels import (
    verdict_from_probs, UI_UNCERTAIN, UNCERTAINTY_THRESHOLD,
)

_backend = None   # lazily imported backend modules


class BackendError(RuntimeError):
    """Raised when the ML backend can't be loaded or run."""


def _load_backend():
    """Import the backend modules once (lazy, so the UI starts instantly)."""
    global _backend
    if _backend is not None:
        return _backend

    backend_dir = find_backend_dir()
    if backend_dir is None:
        raise BackendError(
            "ML backend not found. Expected a folder containing "
            "xgboost_model.json, feature_extraction.py, preprocessing.py ... "
            "(default: the 'backend' folder next to app.py). "
            "You can also set the TRUTHLENS_BACKEND environment variable."
        )

    if str(backend_dir) not in sys.path:
        sys.path.insert(0, str(backend_dir))

    try:
        import xgboost
        major_minor = tuple(int(x) for x in xgboost.__version__.split(".")[:2])
        if major_minor < (3, 1):
            raise BackendError(
                f"xgboost {xgboost.__version__} is too old to load xgboost_model.json "
                "(saved with xgboost 3.2). Run:  pip install -U \"xgboost>=3.1\""
            )
        import preprocessing
        import feature_extraction
        import model_prediction
        import explanation_user_improved
        import source_credibility
        import text_highlights
    except ImportError as e:
        raise BackendError(
            f"Missing Python package for the backend: {e}. "
            "Run:  pip install -r requirements.txt"
        ) from e

    _backend = {
        "dir": backend_dir,
        "preprocessing": preprocessing,
        "feature_extraction": feature_extraction,
        "model_prediction": model_prediction,
        "explanation": explanation_user_improved,
        "source_credibility": source_credibility,
        "text_highlights": text_highlights,
    }
    return _backend


def _f(value, default=0.5):
    """float() that maps None / NaN / garbage to a default.
    Only for OPTIONAL display values (features, credibility). Never use this for
    the model probabilities - see _prob()."""
    try:
        v = float(value)
        return default if math.isnan(v) else v
    except (TypeError, ValueError):
        return default


def _prob(value, name):
    """Model probability. NaN / missing is an ERROR, never silently 0.5
    (that silent default is exactly what used to show a fake 50 / 50)."""
    try:
        v = float(value)
    except (TypeError, ValueError):
        raise BackendError(f"Model returned an invalid {name}: {value!r}")
    if math.isnan(v) or not 0.0 <= v <= 1.0:
        raise BackendError(f"Model returned an invalid {name}: {value!r}")
    return v


def _error_result(message, text, source, title, author, trust_source):
    """Result dict for a FAILED analysis. Contains 'error' so the UI can show
    the failure instead of a fake verdict."""
    return {
        "error": message,
        "prediction": UI_UNCERTAIN,
        "confidence": 0.0,
        "prob_misinfo": None,
        "prob_real": None,
        "text": text,
        "source": source or "Unknown",
        "title": title or "",
        "author": author or "",
        "sentiment": 0.0, "subjectivity": 0.0, "readability": 0.0,
        "exclamation_ratio": 0.0, "uppercase_ratio": 0.0,
        "explanation": f"Error: {message}",
        "source_credibility_score": 0.5,
        "trust_source": trust_source,
    }


def analyze_text(text, source="Unknown", author=None, title=None, trust_source=None):
    """Analyze one article and return a result dict for the UI."""
    temp_dir = None
    try:
        be = _load_backend()
        backend_dir = be["dir"]
        model_path = backend_dir / "xgboost_model.json"
        credibility_path = backend_dir / "source_credibility_lookup.csv"

        # Always-valid scratch folder (fixes "[WinError 3] cannot find the path")
        temp_dir = tempfile.mkdtemp(prefix="truthlens_")
        p = lambda name: str(Path(temp_dir) / name)

        # 1. preprocess
        df = be["preprocessing"].preprocess_user_input(
            text, source if source else "Unknown", title=title, author=author)
        be["preprocessing"].save_preprocessed_output(df, p("preprocessed.csv"))

        # 2. features (DistilBERT 768 + 5 linguistic)
        be["feature_extraction"].extract_features_from_csv(p("preprocessed.csv"), p("features.csv"))

        # 3. prediction
        be["model_prediction"].predict_from_csv(p("features.csv"), str(model_path), p("predictions.csv"))

        # 4 + 5. explanation and source credibility are OPTIONAL extras. If they fail
        # the verdict (which only needs predictions.csv) must still be shown.
        expl_df, cred_df = pd.DataFrame(), pd.DataFrame()
        try:
            be["explanation"].explain_predictions_improved_from_csv(
                p("predictions.csv"), p("features.csv"), p("explanations.csv"))
            expl_df = pd.read_csv(p("explanations.csv"))
            if credibility_path.exists():
                be["source_credibility"].add_source_credibility_from_csv(
                    p("explanations.csv"), str(credibility_path), p("credibility.csv"),
                    model_weight=0.8, source_weight=0.2)
                cred_df = pd.read_csv(p("credibility.csv"))
        except Exception:  # noqa: BLE001
            traceback.print_exc()

        pred_df = pd.read_csv(p("predictions.csv"))
        feat_df = pd.read_csv(p("features.csv"))

        if len(pred_df) == 0:
            raise BackendError("Model returned no prediction.")

        row = pred_df.iloc[0]
        fake_prob, real_prob = _prob(row["fake_prob"], "fake_prob"), _prob(row["real_prob"], "real_prob")
        if abs(fake_prob + real_prob - 1.0) > 0.01:
            raise BackendError(f"Probabilities do not sum to 1: {fake_prob}, {real_prob}")
        label, confidence = verdict_from_probs(fake_prob, real_prob, UNCERTAINTY_THRESHOLD)

        feat = feat_df.iloc[0]
        cred_score = _f(cred_df.iloc[0].get("source_credibility_score"), 0.5) if len(cred_df) else 0.5

        # Passages that actually mattered for THIS text (model occlusion + style cues).
        # Optional extra: never allowed to break the verdict.
        try:
            highlights = be["text_highlights"].compute_highlights(text, str(model_path))
        except Exception:  # noqa: BLE001
            traceback.print_exc()
            highlights = []

        return {
            "text": text,
            "highlights": highlights,
            "source": source if source else "Unknown",
            "title": title or "",
            "author": author or "",
            # UI label + REAL probabilities (never a hard-coded 50/50)
            "prediction": label,
            "confidence": confidence,
            "prob_misinfo": fake_prob,
            "prob_real": real_prob,
            "raw_label": str(row.get("prediction_label", "")),
            "sentiment": _f(feat.get("feature_768"), 0.0),
            "subjectivity": _f(feat.get("feature_769"), 0.0),
            "readability": _f(feat.get("feature_770"), 0.0),
            "exclamation_ratio": _f(feat.get("feature_771"), 0.0),
            "uppercase_ratio": _f(feat.get("feature_772"), 0.0),
            "explanation": str(expl_df.iloc[0].get("explanation", "Analysis complete")) if len(expl_df) else "Analysis complete",
            "source_credibility_score": cred_score,
            "trust_source": trust_source,
        }

    except Exception as e:  # noqa: BLE001 - surfaced to the UI, not swallowed
        traceback.print_exc()
        msg = str(e) or e.__class__.__name__
        return _error_result(msg, text, source, title, author, trust_source)

    finally:
        if temp_dir:
            shutil.rmtree(temp_dir, ignore_errors=True)


# ============================================================
# BATCH ANALYSIS
# ============================================================
def get_highlights(text):
    """Key passages for ONE text (used lazily when a batch case is opened).
    Optional extra: never raises."""
    try:
        be = _load_backend()
        return be["text_highlights"].compute_highlights(
            text, str(be["dir"] / "xgboost_model.json"))
    except Exception:  # noqa: BLE001
        traceback.print_exc()
        return []


def _analyze_chunk(records):
    """Run the pipeline ONCE over a list of records (dicts with text/source/title/author)
    and return one result dict per record, in the same order. Same result schema as
    analyze_text(). Raises on failure so the caller can fall back to per-row analysis."""
    be = _load_backend()
    backend_dir = be["dir"]
    model_path = backend_dir / "xgboost_model.json"
    credibility_path = backend_dir / "source_credibility_lookup.csv"
    temp_dir = tempfile.mkdtemp(prefix="truthlens_batch_")
    p = lambda name: str(Path(temp_dir) / name)
    try:
        pre = pd.DataFrame({
            "text": [r["text"] for r in records],
            "text_cleaned": [be["preprocessing"].normalize_text(r["text"]) for r in records],
            "source": [r.get("source") or "Unknown" for r in records],
        })
        be["preprocessing"].save_preprocessed_output(pre, p("preprocessed.csv"))
        be["feature_extraction"].extract_features_from_csv(p("preprocessed.csv"), p("features.csv"))
        be["model_prediction"].predict_from_csv(p("features.csv"), str(model_path), p("predictions.csv"))

        expl_df, cred_df = pd.DataFrame(), pd.DataFrame()
        try:
            be["explanation"].explain_predictions_improved_from_csv(
                p("predictions.csv"), p("features.csv"), p("explanations.csv"))
            expl_df = pd.read_csv(p("explanations.csv"))
            if credibility_path.exists():
                be["source_credibility"].add_source_credibility_from_csv(
                    p("explanations.csv"), str(credibility_path), p("credibility.csv"),
                    model_weight=0.8, source_weight=0.2)
                cred_df = pd.read_csv(p("credibility.csv"))
        except Exception:  # noqa: BLE001 - optional extras
            traceback.print_exc()

        pred_df = pd.read_csv(p("predictions.csv"))
        feat_df = pd.read_csv(p("features.csv"))
        if not (len(pred_df) == len(feat_df) == len(records)):
            raise BackendError("Model returned a different number of rows than were submitted.")

        results = []
        for i, rec in enumerate(records):
            row, feat = pred_df.iloc[i], feat_df.iloc[i]
            fake_prob, real_prob = _prob(row["fake_prob"], "fake_prob"), _prob(row["real_prob"], "real_prob")
            if abs(fake_prob + real_prob - 1.0) > 0.01:
                raise BackendError(f"Probabilities do not sum to 1: {fake_prob}, {real_prob}")
            label, confidence = verdict_from_probs(fake_prob, real_prob, UNCERTAINTY_THRESHOLD)
            cred_score = _f(cred_df.iloc[i].get("source_credibility_score"), 0.5) if len(cred_df) == len(records) else 0.5
            explanation = (str(expl_df.iloc[i].get("explanation", "Analysis complete"))
                           if len(expl_df) == len(records) else "Analysis complete")
            results.append({
                "text": rec["text"],
                "highlights": [],            # computed on demand when the case is opened
                "source": rec.get("source") or "Unknown",
                "title": rec.get("title") or "",
                "author": rec.get("author") or "",
                "prediction": label,
                "confidence": confidence,
                "prob_misinfo": fake_prob,
                "prob_real": real_prob,
                "raw_label": str(row.get("prediction_label", "")),
                "sentiment": _f(feat.get("feature_768"), 0.0),
                "subjectivity": _f(feat.get("feature_769"), 0.0),
                "readability": _f(feat.get("feature_770"), 0.0),
                "exclamation_ratio": _f(feat.get("feature_771"), 0.0),
                "uppercase_ratio": _f(feat.get("feature_772"), 0.0),
                "explanation": explanation,
                "source_credibility_score": cred_score,
                "trust_source": None,
            })
        return results
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def analyze_batch(records, chunk_size=10, progress_cb=None):
    """Analyze many articles. `records` = list of dicts with keys text (required),
    source / title / author (optional). Returns a list of result dicts in the SAME order;
    a row that could not be analyzed gets a result containing 'error' (like analyze_text).
    progress_cb(done, total) is called after every chunk."""
    total = len(records)
    out = []
    for start in range(0, total, chunk_size):
        chunk = records[start:start + chunk_size]
        try:
            out.extend(_analyze_chunk(chunk))
        except Exception:  # noqa: BLE001 - isolate the bad row(s): retry this chunk row by row
            traceback.print_exc()
            for r in chunk:
                out.append(analyze_text(r["text"], source=r.get("source") or "Unknown",
                                        author=r.get("author"), title=r.get("title")))
        if progress_cb:
            progress_cb(min(start + chunk_size, total), total)
    return out
