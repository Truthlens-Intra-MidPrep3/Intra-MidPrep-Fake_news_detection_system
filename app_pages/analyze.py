"""
analyze.py
==============================================

When user submits:
1. Calls backend processor (internally, not CLI)
2. Gets result
3. Saves to CSV
4. Shows result in Streamlit
"""

import streamlit as st
import pandas as pd
import os
from pathlib import Path

# Import backend processor
from backend_processor import analyze_text, analyze_batch, get_highlights
from csv_to_frontend import (
    get_priority, new_case_id, new_case_ids, get_all_cases, get_case_by_id,
    send_to_review_queue,
)
from datetime import datetime
import io
import json
import re

# Import components
from components.header import render_header
from components.cards import (
    render_prediction_card, render_responsible_use, priority_badge_html,
    set_flash, show_flash,
)
from components.explanations import (
    render_explanation_card, render_signal_breakdown,
    render_text_highlighting, render_supporting_vs_verified,
)
from components.review import render_source_profile


# CSV file path (where results are saved)
CSV_PATH = "../backend/single_article_analysis.csv"
BACKEND_DIR = Path(__file__).parent.parent / "backend"


def result_to_csv_row(result):
    """Convert analysis result dict to CSV-compatible format"""
    return {
        'title': result.get('title', ''),
        'author': result.get('author', ''),
        'text': result.get('text', ''),
        'source': result.get('source', 'Unknown'),
        'prediction': result.get('prediction', 'Uncertain'),
        'confidence': result.get('confidence', 0.5),
        'sentiment': result.get('sentiment', 0.5),
        'subjectivity': result.get('subjectivity', 0.5),
        'readability': result.get('readability', 0.5),
        'exclamation_ratio': result.get('exclamation_ratio', 0.5),
        'uppercase_ratio': result.get('uppercase_ratio', 0.5),
        'source_credibility_score': result.get('source_credibility_score', 0.5),
        'trust_source': result.get('trust_source', None),
        'explanation': result.get('explanation', ''),
        # review tracking (used by Review Queue / History / Review Case)
        'case_id': result.get('case_id'),
        'review_status': 'Pending',
        'in_review_queue': 'No',      # only 'Yes' after "Send to Review Queue"
        'reviewer_label': None,
        'reviewer_note': '',
        'review_history': json.dumps([{"time": datetime.now().strftime("%H:%M"),
                                       "event": "Article submitted for analysis"}]),
        'timestamp': datetime.now().strftime("%H:%M"),
    }


def save_result_to_csv(result):
    """Save result to CSV file"""
    try:
        # Create backend directory if needed
        BACKEND_DIR.mkdir(parents=True, exist_ok=True)
        
        # Convert result to DataFrame
        csv_data = result_to_csv_row(result)
        df = pd.DataFrame([csv_data])
        
        # Append to existing CSV or create new
        csv_path = BACKEND_DIR / "single_article_analysis.csv"
        
        if csv_path.exists():
            existing_df = pd.read_csv(csv_path)
            if 'in_review_queue' not in existing_df.columns:
                existing_df['in_review_queue'] = 'Yes'   # older rows keep their queue behaviour
            df = pd.concat([existing_df, df], ignore_index=True)
        
        # Save
        df.to_csv(csv_path, index=False)
        
        return True
    except Exception as e:
        print(f"Error saving to CSV: {e}")
        return False


def save_results_to_csv(results):
    """Batch version of save_result_to_csv: append MANY results in one write."""
    try:
        BACKEND_DIR.mkdir(parents=True, exist_ok=True)
        df = pd.DataFrame([result_to_csv_row(r) for r in results])
        csv_path = BACKEND_DIR / "single_article_analysis.csv"
        if csv_path.exists():
            existing_df = pd.read_csv(csv_path)
            if 'in_review_queue' not in existing_df.columns:
                existing_df['in_review_queue'] = 'Yes'
            df = pd.concat([existing_df, df], ignore_index=True)
        df.to_csv(csv_path, index=False)
        return True
    except Exception as e:
        print(f"Error saving batch to CSV: {e}")
        return False


def result_dict_to_case(result):
    """Transform result dict to frontend case dict"""
    
    import random
    
    text = result.get('text', '')
    source = result.get('source', 'Unknown')
    prediction = result.get('prediction', 'Uncertain')
    confidence = float(result.get('confidence', 0.5))
    
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
    
    # Priority: High only when the prediction is Uncertain, otherwise Medium / Low
    priority = get_priority(prediction, confidence)
    
    # Categorize features
    def cat(v, kind="ratio"):
        """
        Map a raw feature value to Low / Moderate / High using the RIGHT scale
        for each feature (they are not all 0-1):
        - sentiment          : polarity -1..1, judged by |value| (0 = neutral)
        - subjectivity       : 0..1 (opinion share)
        - readability        : Flesch reading EASE / 100 (high = easy) -> HIGH means hard to read
        - exclamation_ratio  : exclamation marks per sentence
        - uppercase_ratio    : share of capital LETTERS (normal prose is 3-6%)
        """
        try:
            v = float(v)
        except (TypeError, ValueError):
            return "Moderate"
        if kind == "sentiment":
            v = abs(v)
            return "Low" if v < 0.2 else ("Moderate" if v < 0.5 else "High")
        if kind == "subjectivity":
            return "Low" if v < 0.4 else ("Moderate" if v < 0.7 else "High")
        if kind == "readability":          # difficulty = 1 - ease
            d = 1 - v
            return "Low" if d < 0.4 else ("Moderate" if d < 0.7 else "High")
        if kind == "exclamation":
            return "Low" if v < 0.05 else ("Moderate" if v < 0.15 else "High")
        if kind == "uppercase":
            return "Low" if v < 0.07 else ("Moderate" if v < 0.15 else "High")
        return "Moderate"

    src_cred = float(result.get('source_credibility_score', 0.5))
    
    # Parse explanation
    def parse_exp(text):
        if not text or len(str(text)) < 5:
            return [{"feature": "Analysis", "score": 0.5, "label": "Mixed", "text": "Complete"}]
        
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
    
    # Use actual title from result, fallback to first 80 chars of text
    display_title = result.get('title', '')
    if not display_title:
        display_title = text[:80] + "..." if len(text) > 80 else text
    
    # Use actual author from result
    display_author = result.get('author', None)
    if display_author == '':
        display_author = None
    
    case = {
        "case_id": result.get("case_id") or new_case_id(),
        "title": display_title,
        "text": text,
        "source": source,
        "author": display_author,
        
        "prediction": prediction,
        "prob_real": round(prob_real, 3),
        "prob_misinfo": round(prob_misinfo, 3),
        "confidence": round(confidence, 3),
        
        "priority": priority,
        "review_status": "Pending",
        "in_queue": False,
        "source_credibility": round(src_cred, 2),
        "author_credibility": None,
        
        "sentiment": cat(result.get('sentiment', 0.0), "sentiment"),
        "subjectivity": cat(result.get('subjectivity', 0.5), "subjectivity"),
        "readability": cat(result.get('readability', 0.5), "readability"),
        "exclamation_ratio": cat(result.get('exclamation_ratio', 0.0), "exclamation"),
        "uppercase_ratio": cat(result.get('uppercase_ratio', 0.0), "uppercase"),
        "semantic_signal": "Mixed",
        
        "explanation": parse_exp(result.get('explanation', '')),
        "highlights": result.get("highlights", []),   # real spans from the backend
        "highlighted_passages": [],
        
        "reviewer_label": None,
        "reviewer_note": "",
        "timestamp": __import__('datetime').datetime.now().strftime("%H:%M"),
        
        "source_history": {
            "total": random.randint(20, 200),
            "real_pct": src_cred,
        },
        "author_history": {
            "total": 0,
            "real_pct": None,
        },
        "review_history": [
            {"time": __import__('datetime').datetime.now().strftime("%H:%M"), "event": "Article submitted for analysis"}
        ]
    }
    
    return case


def _case_in_queue(case_id):
    """Is this case currently waiting in the Review Queue?"""
    c = get_case_by_id(case_id)
    return bool(c and c["in_queue"] and c["review_status"] == "Pending")


def _display_result(case, remember=True):
    """Display analysis result (remember=False for cases opened from a batch)"""
    if remember:
        st.session_state.analysis_result = case
    st.markdown("---")
    render_prediction_card(case)

    st.markdown("#### Prediction Confidence")
    c1, c2 = st.columns(2)
    c1.metric("Likely Misinformation", f"{case['prob_misinfo']*100:.1f}%")
    c2.metric("Likely Real", f"{case['prob_real']*100:.1f}%")
    conf_label = "High" if case["confidence"] > 0.75 else "Moderate" if case["confidence"] > 0.55 else "Low"
    st.markdown(f"**Calibrated Confidence:** {conf_label}",
                unsafe_allow_html=True)

    st.markdown("---")
    render_explanation_card(case["explanation"])

    st.markdown("---")
    render_text_highlighting(case)

    st.markdown("---")
    render_signal_breakdown(case)

    st.markdown("---")
    render_source_profile(case)

    st.markdown("---")
    st.markdown(f"**Review Priority:** {priority_badge_html(case['priority'])}", unsafe_allow_html=True)
    reason = {
        "High": "The model's prediction is uncertain, so a human reviewer should decide.",
        "Medium": "Moderate signal strength warrants a secondary review pass.",
        "Low": "Low risk signal; queued for routine review.",
    }[case["priority"]]
    st.caption(f"Reason: {reason}")

    if _case_in_queue(case["case_id"]):
        st.success(f"Case {case['case_id']} is in the Review Queue.")
    elif st.button("Send to Review Queue", key=f"send_queue_{case['case_id']}"):
        if send_to_review_queue(case["case_id"]):
            st.rerun()      # refresh: shows "is in the Review Queue" and updates the batch table
        else:
            st.error("Could not add this case to the Review Queue.")
    st.caption("Every analysed case is saved to History automatically.")

    st.markdown("---")
    render_responsible_use()

# ============================================================
# BATCH UPLOAD
# ============================================================
_TEXT_ALIASES = ["text", "content", "article", "body", "claim", "statement",
                 "post", "tweet", "news", "full_text", "description"]
_SOURCE_ALIASES = ["source", "publisher", "site", "domain", "outlet", "website"]
_TITLE_ALIASES = ["title", "headline"]
_AUTHOR_ALIASES = ["author", "authors", "byline"]
_MIN_CHARS = 10          # the model needs at least this much text


def _clean_cell(v):
    if v is None:
        return ""
    try:
        if pd.isna(v):
            return ""
    except (TypeError, ValueError):
        pass
    return str(v).strip()


def parse_batch_file(uploaded):
    """Read an uploaded CSV / TXT / JSON into a list of records.
    Returns (records, skipped_rows). Raises ValueError with a readable message."""
    name = uploaded.name.lower()
    raw = uploaded.getvalue()
    try:
        content = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        content = raw.decode("latin-1")
    if not content.strip():
        raise ValueError("The uploaded file is empty.")

    ext = name.rsplit(".", 1)[-1]
    try:
        if ext == "csv":
            df = pd.read_csv(io.StringIO(content), dtype=str, keep_default_na=False)
        elif ext == "json":
            data = json.loads(content)
            if isinstance(data, dict):
                lists = [v for v in data.values() if isinstance(v, list)]
                data = lists[0] if lists else [data]
            if data and all(isinstance(x, str) for x in data):
                df = pd.DataFrame({"text": data})
            else:
                df = pd.json_normalize(data)
        else:  # txt: items separated by blank lines, or one item per line
            blocks = [b.strip() for b in re.split(r"\n\s*\n", content) if b.strip()]
            if len(blocks) <= 1:
                blocks = [ln.strip() for ln in content.splitlines() if ln.strip()]
            df = pd.DataFrame({"text": blocks})
    except Exception as e:  # noqa: BLE001
        raise ValueError(f"Could not read this file as {ext.upper()}: {e}")

    if len(df) == 0:
        raise ValueError("No rows found in the uploaded file.")

    lower = {str(c).strip().lower(): c for c in df.columns}
    pick = lambda aliases: next((lower[a] for a in aliases if a in lower), None)
    text_col = pick(_TEXT_ALIASES)
    if text_col is None and len(df.columns) == 1:
        text_col = df.columns[0]
    if text_col is None:
        raise ValueError(
            "Couldn't find the text column. Add a column named 'text' "
            f"(found: {', '.join(map(str, df.columns))})."
        )
    source_col, title_col, author_col = pick(_SOURCE_ALIASES), pick(_TITLE_ALIASES), pick(_AUTHOR_ALIASES)
    mapped = {text_col, source_col, title_col, author_col}

    records, skipped = [], []
    for i, row in enumerate(df.to_dict("records"), start=1):
        text = _clean_cell(row.get(text_col))
        if len(text) < _MIN_CHARS:
            skipped.append(i)
            continue
        records.append({
            "row": i,
            "text": text,
            "source": _clean_cell(row.get(source_col)) if source_col else "",
            "title": _clean_cell(row.get(title_col)) if title_col else "",
            "author": _clean_cell(row.get(author_col)) if author_col else "",
            "extra": {str(k): _clean_cell(v) for k, v in row.items() if k not in mapped},
        })
    if not records:
        raise ValueError(f"No usable rows: every row had fewer than {_MIN_CHARS} characters of text.")
    return records, skipped


def _run_batch(uploaded):
    """Parse -> analyze -> give every case an ID -> save ALL to History -> keep for display."""
    try:
        records, skipped = parse_batch_file(uploaded)
    except ValueError as e:
        st.error(str(e))
        return

    bar = st.progress(0.0, text=f"Analyzing {len(records)} items... this can take a while")

    def _progress(done, total):
        bar.progress(done / total, text=f"Analyzed {done} of {total}")

    results = analyze_batch(records, progress_cb=_progress)
    bar.empty()

    entries, ok = [], []
    for rec, res in zip(records, results):
        entries.append({"row": rec["row"], "extra": rec["extra"], "result": res})
        if not res.get("error"):
            ok.append(res)

    if ok:
        for res, cid in zip(ok, new_case_ids(len(ok))):
            res["case_id"] = cid
        if not save_results_to_csv(ok):
            st.error("Error saving results to CSV")
            return

    cases = [result_dict_to_case(r) for r in ok]
    failed = [{"row": e["row"], "error": e["result"]["error"]}
              for e in entries if e["result"].get("error")]
    st.session_state.batch_result = {
        "filename": uploaded.name,
        "total": len(cases),
        "likely_real": sum(c["prediction"] == "Likely Real" for c in cases),
        "uncertain": sum(c["prediction"] == "Uncertain" for c in cases),
        "likely_misinfo": sum(c["prediction"] == "Likely Misinformation" for c in cases),
        "flagged": sum(c["prediction"] == "Likely Misinformation" for c in cases),
        "high_priority": sum(c["priority"] == "High" for c in cases),
        "medium_priority": sum(c["priority"] == "Medium" for c in cases),
        "low_priority": sum(c["priority"] == "Low" for c in cases),
        "rows": cases,
        "entries": entries,
        "failed": failed,
        "skipped": skipped,
    }
    st.session_state.pop("_batch_highlights", None)


def _batch_csv_bytes(batch):
    """Final CSV: every input row with its prediction, probabilities, signals and explanation."""
    queued = {c["case_id"] for c in get_all_cases() if c["in_queue"] and c["review_status"] == "Pending"}
    out = []
    for e in batch["entries"]:
        r = e["result"]
        failed = bool(r.get("error"))
        row = {
            "case_id": "" if failed else r.get("case_id", ""),
            "input_row": e["row"],
            "title": r.get("title", ""),
            "author": r.get("author", ""),
            "source": r.get("source", ""),
            "text": r.get("text", ""),
            "prediction": "Error" if failed else r.get("prediction", ""),
            "confidence (%)": "" if failed else round(float(r.get("confidence", 0)) * 100, 1),
            "likely_misinformation (%)": "" if failed else round(float(r.get("prob_misinfo", 0)) * 100, 1),
            "likely_real (%)": "" if failed else round(float(r.get("prob_real", 0)) * 100, 1),
            "review_priority": "" if failed else get_priority(r.get("prediction"), r.get("confidence")),
            "source_credibility_score": "" if failed else r.get("source_credibility_score", ""),
            "sentiment": "" if failed else r.get("sentiment", ""),
            "subjectivity": "" if failed else r.get("subjectivity", ""),
            "readability": "" if failed else r.get("readability", ""),
            "exclamation_ratio": "" if failed else r.get("exclamation_ratio", ""),
            "uppercase_ratio": "" if failed else r.get("uppercase_ratio", ""),
            "explanation": r.get("explanation", ""),
            "in_review_queue": "" if failed else ("Yes" if r.get("case_id") in queued else "No"),
        }
        for k, v in e["extra"].items():
            row[f"input_{k}"] = v
        out.append(row)
    buf = io.StringIO()
    pd.DataFrame(out).to_csv(buf, index=False)
    return buf.getvalue().encode("utf-8-sig")      # utf-8-sig so Excel shows icons correctly


def _render_batch_results(batch):
    st.markdown("---")
    st.markdown("#### Batch Results")
    st.caption(f"File: {batch['filename']}")

    existing = {c["case_id"]: c for c in get_all_cases()}      # live state (also drops deleted cases)
    cases = [c for c in batch["rows"] if c["case_id"] in existing]

    m = st.columns(4)
    m[0].metric("Analyzed", batch["total"])
    m[1].metric("Likely Real", batch["likely_real"])
    m[2].metric("Uncertain", batch["uncertain"])
    m[3].metric("Likely Misinformation", batch["likely_misinfo"])

    if batch["skipped"]:
        st.warning(f"Skipped {len(batch['skipped'])} row(s) with missing or too-short text "
                   f"(rows: {', '.join(map(str, batch['skipped'][:20]))}"
                   f"{'...' if len(batch['skipped']) > 20 else ''}).")
    if batch["failed"]:
        with st.expander(f"⚠ {len(batch['failed'])} row(s) could not be analyzed"):
            for f in batch["failed"]:
                st.markdown(f"- Row {f['row']}: {f['error']}")
    if batch["total"]:
        st.success(f"✓ {batch['total']} case(s) saved to History.")

    st.download_button(
        "⬇ Download Results (CSV)",
        data=_batch_csv_bytes(batch),
        file_name=f"truthlens_batch_results_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
        mime="text/csv",
        key="batch_dl_csv",
    )

    if not cases:
        st.info("No cases from this batch are left in History.")
        return

    def _in_q(cid):
        c = existing[cid]
        return c["in_queue"] and c["review_status"] == "Pending"

    st.dataframe(
        pd.DataFrame([{
            "Case ID": c["case_id"],
            "Title": c["title"],
            "Source": c["source"],
            "Prediction": c["prediction"],
            "Confidence": f"{c['confidence']*100:.1f}%",
            "Priority": c["priority"],
            "Review Queue": "✓ Queued" if _in_q(c["case_id"]) else "—",
        } for c in cases]),
        use_container_width=True, hide_index=True,
    )

    label = lambda cid: f"{cid} — {existing[cid]['title'][:70]}"
    ids = [c["case_id"] for c in cases]

    st.markdown("##### Send to Review Queue (optional)")
    st.caption("Nothing goes to the Review Queue unless you choose it. All cases stay in History either way.")
    sendable = [i for i in ids if not _in_q(i)]
    chosen = st.multiselect("Cases to send", sendable, format_func=label, key="batch_send_select")
    if st.button("Send selected to Review Queue", key="batch_send_btn", disabled=not chosen):
        done = sum(1 for cid in chosen if send_to_review_queue(cid))
        set_flash(f"Sent {done} case(s) to the Review Queue.")
        st.rerun()

    st.markdown("---")
    st.markdown("#### View a Case")
    selected = st.selectbox("Select case", ids, format_func=label, key="batch_case_select")
    case = dict(next(c for c in cases if c["case_id"] == selected))

    cache = st.session_state.setdefault("_batch_highlights", {})
    if selected not in cache:
        with st.spinner("Finding key passages..."):
            cache[selected] = get_highlights(case["text"])
    case["highlights"] = cache[selected]
    _display_result(case, remember=False)


def render():
    """Main analyze page"""
    render_header("Analyze Content", "Submit content for model-based misinformation risk assessment")

    tab1, tab2 = st.tabs(["📝 Single Article", "📦 Batch Upload"])

    with tab1:
        content_type = st.selectbox("Content Type", ["News Article", "Social Media Post", "Claim / Statement", "Other"])
        c1, c2 = st.columns(2)
        source = c1.text_input("Source", placeholder="Optional source name")
        author = c2.text_input("Author", placeholder="Optional author")
        title = st.text_input("Title", placeholder="Optional title")
        
        content = st.text_area(
            "Main Content", height=200,
            placeholder="Paste a news article, social media post, claim, or other textual content here...",
        )
        
        if st.button("🔍 Analyze Content", type="primary"):
            if not content.strip():
                st.warning("Please paste some content to analyze.")
            else:
                with st.spinner("Analyzing... Please wait"):
                    # Call backend processor
                    result = analyze_text(
                        text=content,
                        source=source if source else "Unknown",
                        author=author if author else None,
                        title=title if title else None,
                        trust_source=None
                    )
                    
                    # Give the case its permanent ID, then save to CSV
                    result["case_id"] = new_case_id()
                    if save_result_to_csv(result):
                        st.success("✓ Analysis complete and saved!")
                        
                        # Convert to case dict and display
                        case = result_dict_to_case(result)
                        _display_result(case)
                    else:
                        st.error("Error saving results to CSV")
        
        elif st.session_state.get("analysis_result"):
            _display_result(st.session_state.analysis_result)

    with tab2:
        st.markdown("Upload a dataset containing multiple content items.")
        st.caption("Supported formats: CSV · TXT · JSON")
        st.caption("CSV / JSON need a 'text' column (optional: source, title, author). "
                   "TXT: one item per line, or items separated by blank lines.")
        uploaded = st.file_uploader("Upload dataset", type=["csv", "txt", "json"])
        show_flash()
        if st.button("Analyze Batch", type="primary"):
            if uploaded is None:
                st.warning("Please upload a file first.")
            else:
                _run_batch(uploaded)

        if st.session_state.get("batch_result"):
            _render_batch_results(st.session_state.batch_result)
