"""
csv_to_frontend.py 
"""

import os
import json
import math
import random
import pandas as pd
from pathlib import Path
from datetime import datetime

from labels import to_ui_label
from paths import RESULTS_DIR

# CSV paths to look for
CSV_SEARCH_PATHS = [
    str(RESULTS_DIR / "single_article_analysis.csv"),
    "backend/single_article_analysis.csv",
    "backend/batch_analysis_results.csv",
    "../backend/single_article_analysis.csv",
    "../backend/batch_analysis_results.csv",
    "single_article_analysis.csv",
    "batch_analysis_results.csv",
]


def find_csv():
    """Find the backend CSV file"""
    for path in CSV_SEARCH_PATHS:
        if os.path.exists(path):
            return path
    return None


# Review-tracking columns stored in the CSV next to the analysis columns
REVIEW_COLS = ["case_id", "review_status", "reviewer_label",
               "reviewer_note", "review_history", "timestamp"]

# "Yes" only when someone explicitly sent the case to the Review Queue.
# Every analysed case (single or batch) is in History regardless of this flag.
QUEUE_COL = "in_review_queue"


def _now():
    return datetime.now().strftime("%H:%M")


def _blank(v):
    """True for None / NaN / empty string."""
    if v is None:
        return True
    if isinstance(v, float) and math.isnan(v):
        return True
    return str(v).strip() == ""


def _s(v, default=""):
    """CSV cell -> clean string (NaN -> default)."""
    return default if _blank(v) else str(v)


def _history_json(events):
    return json.dumps(events, ensure_ascii=False)


def _initial_history(time_str):
    return [{"time": time_str, "event": "Article submitted for analysis"}]


def _parse_history(v, fallback_time=None):
    """CSV cell -> list of {time, event}. Never raises, never returns None."""
    try:
        data = json.loads(v) if not _blank(v) else []
        if isinstance(data, list):
            return [d for d in data if isinstance(d, dict) and "event" in d]
    except (TypeError, ValueError):
        pass
    return _initial_history(fallback_time or _now())


def _ensure_schema(df):
    """Add the review columns + a permanent case_id to every row. Returns (df, changed)."""
    changed = False
    # Rows saved before the "in_review_queue" column existed keep behaving as before
    # (they were all in the queue while Pending). New rows are only queued on request.
    if QUEUE_COL not in df.columns:
        df[QUEUE_COL] = "Yes"
        changed = True
    df[QUEUE_COL] = df[QUEUE_COL].astype(object)
    for col in REVIEW_COLS:
        if col not in df.columns:
            df[col] = None
            changed = True
        df[col] = df[col].astype(object)

    used = {str(x) for x in df["case_id"] if not _blank(x)}
    nums = [int(u.lstrip("#")) for u in used if u.lstrip("#").isdigit()]
    next_n = max(nums + [1000]) + 1

    for pos, idx in enumerate(df.index):
        if _blank(df.at[idx, "case_id"]):
            cand = f"#{1001 + pos}"          # keeps the IDs existing rows already had
            if cand in used:
                cand = f"#{next_n}"
                next_n += 1
            df.at[idx, "case_id"] = cand
            used.add(cand)
            changed = True
        if _blank(df.at[idx, "review_status"]):
            df.at[idx, "review_status"] = "Pending"
            changed = True
        if _blank(df.at[idx, "timestamp"]):
            df.at[idx, "timestamp"] = _now()
            changed = True
        if _blank(df.at[idx, "review_history"]):
            df.at[idx, "review_history"] = _history_json(_initial_history(df.at[idx, "timestamp"]))
            changed = True
    return df, changed


def _save_csv(df):
    csv_path = find_csv()
    if not csv_path:
        return False
    df.to_csv(csv_path, index=False)
    return True


def load_csv():
    """Load CSV safely, return None if not found"""
    csv_path = find_csv()
    if not csv_path:
        return None
    try:
        df = pd.read_csv(csv_path)
        df, changed = _ensure_schema(df)
        if changed:
            try:
                df.to_csv(csv_path, index=False)
            except Exception:
                pass
        return df
    except Exception:
        return None


def new_case_id():
    """Next free permanent case ID, e.g. '#1010'."""
    df = load_csv()
    if df is None or len(df) == 0:
        return "#1001"
    nums = [int(str(x).lstrip("#")) for x in df["case_id"] if str(x).lstrip("#").isdigit()]
    return f"#{max(nums + [1000]) + 1}"


def new_case_ids(n):
    """The next n free permanent case IDs (used by batch analysis)."""
    first = int(new_case_id().lstrip("#"))
    return [f"#{first + i}" for i in range(n)]


def categorize(val):
    """Convert numeric (0-1) to categorical"""
    try:
        v = float(val)
        if v < 0.33:
            return "Low"
        elif v < 0.66:
            return "Moderate"
        else:
            return "High"
    except:
        return "Moderate"


def get_priority(pred, conf=None):
    """High only when the prediction is Uncertain; otherwise Medium or Low."""
    pred = to_ui_label(pred)
    if pred == "Uncertain":
        return "High"
    if pred == "Likely Misinformation":
        return "Medium"
    return "Low"


def parse_explanation(text):
    """Parse explanation text"""
    if not text or not isinstance(text, str) or len(str(text)) < 5:
        return [{"feature": "Analysis", "score": 0.5, "label": "Mixed", "text": "Result"}]
    
    features = []
    for line in str(text).split('\n')[:5]:
        if ':' in line:
            parts = line.split(':', 1)
            fname = parts[0].strip()
            ftext = parts[1].strip() if len(parts) > 1 else ""
            
            import re
            score = 0.5
            match = re.search(r'0\.\d+', ftext)
            if match:
                try:
                    score = float(match.group())
                except:
                    pass
            
            features.append({
                "feature": fname,
                "score": round(score, 3),
                "label": "High" if score > 0.66 else ("Moderate" if score > 0.33 else "Low"),
                "text": ftext[:200]
            })
    
    return features if features else [{"feature": "Assessment", "score": 0.5, "label": "Mixed", "text": str(text)[:200]}]


def csv_row_to_case(row, case_id):
    """Transform CSV row to frontend case dict"""
    
    text = str(row.get('text', ''))
    source = str(row.get('source', 'Unknown'))
    prediction = to_ui_label(row.get('prediction', 'Uncertain'))
    
    try:
        confidence = float(row.get('confidence', 0.5))
    except:
        confidence = 0.5
    
    # Probabilities
    if prediction == 'Likely Misinformation':
        prob_misinfo = confidence
        prob_real = 1 - confidence
    elif prediction == 'Likely Real':
        prob_real = confidence
        prob_misinfo = 1 - confidence
    else:
        prob_misinfo = 0.5
        prob_real = 0.5
    
    # Credibility
    try:
        src_cred = float(row.get('source_credibility_score', 0.5))
    except:
        src_cred = 0.5
    
    # Case dict
    case = {
        "case_id": _s(row.get('case_id'), case_id),
        "title": text[:80] + "..." if len(text) > 80 else text,
        "text": text,
        "source": source,
        "author": None,
        
        "prediction": prediction,
        "prob_real": round(prob_real, 3),
        "prob_misinfo": round(prob_misinfo, 3),
        "confidence": round(confidence, 3),
        
        "priority": get_priority(prediction, confidence),
        "review_status": _s(row.get('review_status'), "Pending"),
        "in_queue": _s(row.get(QUEUE_COL), "No") == "Yes",
        "source_credibility": round(src_cred, 2),
        "author_credibility": None,
        
        "sentiment": categorize(row.get('sentiment', 0.5)),
        "subjectivity": categorize(row.get('subjectivity', 0.5)),
        "readability": categorize(row.get('readability', 0.5)),
        "exclamation_ratio": categorize(row.get('exclamation_ratio', 0.5)),
        "uppercase_ratio": categorize(row.get('uppercase_ratio', 0.5)),
        "semantic_signal": "Mixed",
        
        "explanation": parse_explanation(row.get('explanation', '')),
        "highlighted_passages": [{"text": text[:100], "type": "semantic"}],
        
        "reviewer_label": _s(row.get('reviewer_label')) or None,
        "reviewer_note": _s(row.get('reviewer_note')),
        "timestamp": _s(row.get('timestamp'), _now()),
        "review_history": _parse_history(row.get('review_history'), _s(row.get('timestamp'), _now())),
        
        "source_history": {
            "total": random.randint(20, 200),
            "real_pct": src_cred,
        },
        "author_history": {
            "total": 0,
            "real_pct": None,
        }
    }
    
    return case


# ============================================================
# PUBLIC API
# ============================================================

def get_all_cases():
    """Get all cases from CSV"""
    df = load_csv()
    if df is None or len(df) == 0:
        return []
    
    cases = []
    for idx, row in df.iterrows():
        case = csv_row_to_case(row, f"#{1001 + idx}")
        cases.append(case)
    
    return cases


def get_case_by_id(case_id):
    """Get case by ID"""
    cases = get_all_cases()
    for case in cases:
        if case["case_id"] == case_id:
            return case
    return None


def update_review(case_id, status, reviewer_label=None, note=None, events=None):
    """Persist a review decision to the CSV (single source of truth for the whole app).
    note=None leaves the stored note unchanged. The model's prediction is never touched."""
    df = load_csv()
    if df is None:
        return False
    rows = df.index[df["case_id"].astype(str) == str(case_id)]
    if len(rows) == 0:
        return False
    i = rows[0]
    history = _parse_history(df.at[i, "review_history"], _s(df.at[i, "timestamp"], _now()))
    now = _now()
    for ev in (events or []):
        history.append({"time": now, "event": ev})
    if note is not None:
        df.at[i, "reviewer_note"] = note
        if note.strip():
            history.append({"time": now, "event": "Reviewer note added"})
    df.at[i, "review_status"] = status
    df.at[i, "reviewer_label"] = reviewer_label
    df.at[i, "review_history"] = _history_json(history)
    return _save_csv(df)


def send_to_review_queue(case_id):
    """Explicit 'Send to Review Queue'. The case stays in History either way."""
    df = load_csv()
    if df is None:
        return False
    rows = df.index[df["case_id"].astype(str) == str(case_id)]
    if len(rows) == 0:
        return False
    i = rows[0]
    history = _parse_history(df.at[i, "review_history"], _s(df.at[i, "timestamp"], _now()))
    history.append({"time": _now(), "event": "Sent to Review Queue"})
    df.at[i, QUEUE_COL] = "Yes"
    df.at[i, "review_status"] = "Pending"
    df.at[i, "review_history"] = _history_json(history)
    return _save_csv(df)


def mark_review_done(case_id):
    """'Review Done' button: mark the case Confirmed (model flag confirmed).
    Any non-Pending case leaves the Review Queue and appears in History."""
    case = get_case_by_id(case_id)
    if case is None:
        return False
    return update_review(case_id, "Confirmed", case["prediction"],
                         events=["Reviewer confirmed the model flag"])


def reopen_case(case_id):
    """Send a reviewed case back to the Review Queue (status -> Pending, reviewer opinion cleared)."""
    ok = update_review(case_id, "Pending", None, events=["Case moved back to Review Queue"])
    if not ok:
        return False
    df = load_csv()
    rows = df.index[df["case_id"].astype(str) == str(case_id)]
    if len(rows):
        df.at[rows[0], QUEUE_COL] = "Yes"      # back in the queue, not just "Pending"
        return _save_csv(df)
    return True


def delete_case(case_id):
    """Remove the case from the CSV, so it disappears from Queue, History, Review Case and Reports."""
    df = load_csv()
    if df is None:
        return False
    keep = df["case_id"].astype(str) != str(case_id)
    if keep.all():
        return False
    df = df[keep]
    if not _save_csv(df):
        return False
    try:
        import streamlit as st
        if st.session_state.get("selected_case") == case_id:
            st.session_state.selected_case = None
        ar = st.session_state.get("analysis_result")
        if ar and ar.get("case_id") == case_id:
            st.session_state.analysis_result = None
    except Exception:
        pass
    return True


def queue_stats():
    """Queue statistics"""
    cases = get_all_cases()
    pending = [c for c in cases if c["review_status"] == "Pending" and c["in_queue"]]
    
    return {
        "pending": len(pending),
        "high_priority": len([c for c in pending if c["priority"] == "High"]),
        "uncertain": len([c for c in pending if c["prediction"] == "Uncertain"]),
        "reviewed_today": len([c for c in cases if c["review_status"] != "Pending"]),
        "relabeled": len([c for c in cases if c["review_status"] == "Relabeled"]),
    }


def overview_stats():
    """Overview statistics"""
    cases = get_all_cases()
    total = len(cases)
    
    real = len([c for c in cases if c["prediction"] == "Likely Real"])
    uncertain = len([c for c in cases if c["prediction"] == "Uncertain"])
    misinfo = len([c for c in cases if c["prediction"] == "Likely Misinformation"])
    
    return {
        "total_analyzed": total,
        "likely_real": real,
        "uncertain": uncertain,
        "likely_misinfo": misinfo,
        "pending_review": len([c for c in cases if c["review_status"] == "Pending"]),
        "reviewed": len([c for c in cases if c["review_status"] != "Pending"]),
    }


def mock_analyze_content(title="", source="", author="", content=""):
    """Return random case from CSV"""
    cases = get_all_cases()
    
    if not cases:
        return {
            "case_id": "#0",
            "title": "No data",
            "text": "Run backend first",
            "source": "Unknown",
            "author": None,
            "prediction": "Uncertain",
            "prob_real": 0.5,
            "prob_misinfo": 0.5,
            "confidence": 0.5,
            "priority": "Low",
            "review_status": "Pending",
            "source_credibility": 0.5,
            "author_credibility": None,
            "sentiment": "Neutral",
            "subjectivity": "Moderate",
            "readability": "Moderate",
            "exclamation_ratio": "Low",
            "uppercase_ratio": "Low",
            "semantic_signal": "Mixed",
            "explanation": [{"feature": "Error", "score": 0.0, "label": "Low", "text": "No CSV"}],
            "highlighted_passages": [],
            "reviewer_label": None,
            "reviewer_note": "",
            "timestamp": datetime.now().strftime("%H:%M"),
            "source_history": {"total": 0, "real_pct": 0.5},
            "author_history": {"total": 0, "real_pct": None},
        }
    
    if source:
        matching = [c for c in cases if c["source"].lower() == source.lower()]
        if matching:
            return random.choice(matching)
    
    return random.choice(cases)


def mock_analyze_batch(n=100):
    """Batch analysis"""
    cases = get_all_cases()
    
    if not cases:
        return {
            "total": 0,
            "likely_real": 0,
            "uncertain": 0,
            "likely_misinfo": 0,
            "flagged": 0,
            "high_priority": 0,
            "medium_priority": 0,
            "low_priority": 0,
            "rows": [],
        }
    
    rows = cases[:min(n, len(cases))]
    
    real = len([c for c in rows if c["prediction"] == "Likely Real"])
    uncertain = len([c for c in rows if c["prediction"] == "Uncertain"])
    misinfo = len([c for c in rows if c["prediction"] == "Likely Misinformation"])
    
    high = len([c for c in rows if c["priority"] == "High"])
    med = len([c for c in rows if c["priority"] == "Medium"])
    low = len([c for c in rows if c["priority"] == "Low"])
    
    return {
        "total": len(rows),
        "likely_real": real,
        "uncertain": uncertain,
        "likely_misinfo": misinfo,
        "flagged": misinfo,
        "high_priority": high,
        "medium_priority": med,
        "low_priority": low,
        "rows": rows,
    }


# Compatibility
MODEL_METRICS = {
    "accuracy": 0.880,
    "precision": 0.861,
    "recall": 0.843,
    "f1": 0.852,
    "auc": 0.912,
    "confusion_matrix": {"tp": 412, "fp": 61, "tn": 588, "fn": 74},
}

FAILURE_CASES = [
    {
        "type": "False Positive",
        "model": "Likely Misinformation",
        "truth": "Real",
        "explanation": "Model over-weighted stylistic signals.",
    },
    {
        "type": "False Negative",
        "model": "Likely Real",
        "truth": "Misinformation",
        "explanation": "Model missed emotionally manipulative framing.",
    },
]
