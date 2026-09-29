from datetime import datetime

import streamlit as st

from .cards import set_flash, render_progress_bar, prediction_badge_html, status_badge_html
from .charts import source_history_donut
import pandas as pd
from csv_to_frontend import update_review


def render_source_profile(case):
    st.markdown("#### Source Profile")
    if not case.get("source"):
        st.info("Source information unavailable")
        return
    
    st.markdown(f"**Source:** {case['source']}")
    if case.get('author'):
        st.markdown(f"**Author:** {case['author']}")
    
    st.markdown("**Do you trust this source?**")
    c1, c2, c3 = st.columns(3)
    
    trust_status = case.get('trust_source', None)
    
    if c1.button("👍 Yes, I trust it", key=f"trust_yes_{case.get('case_id', 'unknown')}"):
        trust_status = "trusted"
        st.success("Source marked as trusted")
    
    if c2.button("❓ Neutral", key=f"trust_neutral_{case.get('case_id', 'unknown')}"):
        trust_status = "neutral"
        st.info("Source credibility marked as neutral")
    
    if c3.button("👎 No, I don't trust it", key=f"trust_untrusted_{case.get('case_id', 'unknown')}"):
        trust_status = "untrusted"
        st.warning("Source marked as untrustworthy")
    
    # Display previous decision if exists
    if case.get('trust_source'):
        st.caption(
            f"💾 Previous decision on this source: **{case['trust_source']}**"
        )


def render_review_controls(case, key_prefix=""):
    st.markdown("#### 👤 Your Review")
    st.markdown(
        f"""
        <div class="tl-card">
            <div class="tl-card-title">Model Prediction — original, never overwritten by a review</div>
            {prediction_badge_html(case['prediction'])}
            <span style="margin-left:0.6rem; color:#475569;">Confidence: {case['confidence']*100:.1f}%</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("**Reviewer Action**")
    action = st.radio(
        "Reviewer Action",
        ["✅ Confirm model flag", "🚫 Dismiss model flag", "✏️ Assign corrected label"],
        horizontal=True,
        key=f"{key_prefix}_action_{case['case_id']}",
        label_visibility="collapsed",
    )

    corrected_label = None
    if action == "✏️ Assign corrected label":
        corrected_label = st.selectbox(
            "Corrected label",
            ["Likely Real", "Uncertain", "Likely Misinformation"],
            key=f"{key_prefix}_corrected_{case['case_id']}",
        )
        st.caption(
            "This corrected label is recorded as the reviewer's opinion only. It is stored "
            "alongside — not in place of — the model's original prediction shown above."
        )

    note = st.text_area(
        "Supporting note (optional)",
        key=f"{key_prefix}_note_{case['case_id']}",
        placeholder="Add supporting context for this decision (optional)...",
    )

    if st.button("Submit Review", key=f"{key_prefix}_submit_{case['case_id']}", type="primary"):
        if action == "✅ Confirm model flag":
            new_status = "Confirmed"
            reviewer_label = case["prediction"]
            event = "Reviewer confirmed the model flag"
        elif action == "🚫 Dismiss model flag":
            new_status = "Dismissed"
            reviewer_label = None
            event = "Reviewer dismissed the model flag"
        else:
            new_status = "Relabeled"
            reviewer_label = corrected_label
            event = f"Reviewer assigned corrected label: {corrected_label}"

        # Persisted to the CSV so Review Queue stats, History and Review Case all
        # show the same state. case["prediction"] (the model's original output) is
        # never modified: only status / reviewer label / note are written.
        if not update_review(case["case_id"], new_status, reviewer_label,
                             note=note, events=[event]):
            st.error("Could not save this review.")
            return

        st.session_state[f"review_updated_{case['case_id']}"] = True
        set_flash(
            f"Review submitted — case {case['case_id']} marked as {new_status} and moved to History. "
            f"Model prediction remains {case['prediction']}."
        )
        st.rerun()


def render_model_vs_human(case):
    st.markdown("#### Model vs Human Review")
    c1, c2 = st.columns(2)
    with c1:
        st.markdown(
            f"""<div class="tl-card"><div class="tl-card-title">Model Prediction (original)</div>
            {prediction_badge_html(case['prediction'])}
            <div style="margin-top:0.4rem;">{case['confidence']*100:.1f}% confidence</div></div>""",
            unsafe_allow_html=True,
        )
    with c2:
        human_label = case["reviewer_label"] or "Not yet reviewed"
        badge = prediction_badge_html(human_label) if human_label in (
            "Likely Real", "Uncertain", "Likely Misinformation") else f"<i>{human_label}</i>"
        st.markdown(
            f"""<div class="tl-card"><div class="tl-card-title">Reviewer Opinion</div>
            {badge}
            <div style="margin-top:0.4rem;">{status_badge_html(case['review_status'])}</div></div>""",
            unsafe_allow_html=True,
        )
    if case.get("reviewer_note"):
        st.caption(f"Reviewer note: {case['reviewer_note']}")


def render_review_history(case):
    st.markdown("#### Review History")
    for item in case.get("review_history", []):
        st.markdown(
            f"""
            <div class="tl-timeline-item">
                <div class="tl-timeline-time">{item['time']}</div>
                <div>{item['event']}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )


def render_case_timeline(case):
    stages = ["Submitted", "Analyzed", "Flagged" if case["prediction"] != "Likely Real" else "Cleared",
              "Added to Review Queue", "Reviewer Opened", "Decision", "Stored"]
    reached = 7 if case["review_status"] != "Pending" else 4
    cols = st.columns(len(stages))
    for i, (col, stage) in enumerate(zip(cols, stages)):
        with col:
            done = i < reached
            st.markdown(
                f"<div style='text-align:center; font-size:0.72rem; color:{'#b45309' if done else '#a8a29e'};'>"
                f"{'●' if done else '○'}<br/>{stage}</div>",
                unsafe_allow_html=True,
            )
