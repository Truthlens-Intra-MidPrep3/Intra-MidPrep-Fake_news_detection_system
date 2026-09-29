import streamlit as st

from csv_to_frontend import get_all_cases, queue_stats, mark_review_done, delete_case
from components.cards import (
    render_empty_state, PRIORITY_META, VERDICT_META, STATUS_META, set_flash, show_flash,
)
from components.charts import priority_radar_chart


def render_queue_intro():
    """Compact top-of-page introduction for a first-time reviewer."""
    st.markdown(
        """
        <div class="tl-card" style="padding:1rem 1.3rem; margin-bottom:0.8rem;">
            <div style="font-size:1.4rem; font-weight:800; color:#0f172a;">🚨 Review Queue</div>
            <div style="color:#475569; margin-top:0.15rem; font-size:0.95rem;">
                Review content that has been flagged by the AI system and requires human assessment.
            </div>
            <div style="color:#64748b; margin-top:0.5rem; font-size:0.85rem; line-height:1.4;">
                The AI has already analyzed these cases. Reviewers can inspect the model's prediction,
                confidence, explanations, and supporting information before making a human decision.
            </div>
            <div style="margin-top:0.75rem; font-size:0.82rem; color:#334155; display:flex; align-items:center; flex-wrap:wrap; gap:0.4rem;">
                <span class="tl-badge" style="background:#fdf2f8; color:#be185d;">1. Select a case</span>
                <span style="color:#94a3b8;">→</span>
                <span class="tl-badge" style="background:#fdf2f8; color:#be185d;">2. Inspect the AI assessment</span>
                <span style="color:#94a3b8;">→</span>
                <span class="tl-badge" style="background:#fdf2f8; color:#be185d;">3. Review supporting information</span>
                <span style="color:#94a3b8;">→</span>
                <span class="tl-badge" style="background:#fdf2f8; color:#be185d;">4. Make a human decision</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_priority_legend():
    """Compact legend explaining the queue's color coding."""
    st.markdown(
        """
        <div class="tl-card" style="padding:0.7rem 1.1rem; margin-bottom:0.8rem;">
            <div class="tl-card-title" style="margin-bottom:0.45rem;">Priority &amp; Status</div>
            <div style="display:flex; gap:1.5rem; flex-wrap:wrap; font-size:0.88rem; color:#334155;">
                <span>🔴 High Priority</span>
                <span>🟠 Medium Priority</span>
                <span>🟡 Low Priority</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render():
    render_queue_intro()
    show_flash()

    stats = queue_stats()
    cols = st.columns(5)
    cols[0].metric("Pending Reviews", stats["pending"])
    cols[1].metric("High Priority", stats["high_priority"])
    cols[2].metric("Uncertain", stats["uncertain"])
    cols[3].metric("Reviewed Today", stats["reviewed_today"])
    cols[4].metric("Relabeled", stats["relabeled"])

    st.markdown("---")
    st.markdown("#### Filters")
    f1, f2, f3 = st.columns(3)
    pred_filter = f1.selectbox("Prediction Category", ["All", "Likely Real", "Uncertain", "Likely Misinformation"])
    priority_filter = f2.selectbox("Review Priority", ["All", "High", "Medium", "Low"])
    all_sources = sorted(set(c["source"] for c in get_all_cases() if c["review_status"] == "Pending" and c["in_queue"]))
    source_filter = f3.selectbox("Source", ["All Sources"] + all_sources)

    f5, f6 = st.columns([2, 1])
    conf_range = f5.slider("Confidence", 0, 100, (0, 100))
    sort_by = f6.selectbox("Sort By", ["Review Priority", "Confidence", "Newest", "Oldest"])

    search = st.text_input("Search", placeholder="Search article text, source, case ID")

    # The queue only holds cases that were sent to it and are still awaiting review;
    # every analysed case (and every reviewed one) lives in History.
    cases = [c for c in get_all_cases() if c["review_status"] == "Pending" and c["in_queue"]]
    if pred_filter != "All":
        cases = [c for c in cases if c["prediction"] == pred_filter]
    if priority_filter != "All":
        cases = [c for c in cases if c["priority"] == priority_filter]
    if source_filter != "All Sources":
        cases = [c for c in cases if c["source"] == source_filter]
    cases = [c for c in cases if conf_range[0] <= c["confidence"] * 100 <= conf_range[1]]
    if search:
        s = search.lower()
        cases = [c for c in cases if s in c["text"].lower() or s in c["source"].lower() or s in c["case_id"].lower()]

    priority_rank = {"High": 0, "Medium": 1, "Low": 2}
    if sort_by == "Review Priority":
        cases = sorted(cases, key=lambda c: priority_rank[c["priority"]])
    elif sort_by == "Confidence":
        cases = sorted(cases, key=lambda c: -c["confidence"])
    elif sort_by == "Newest":
        cases = sorted(cases, key=lambda c: c["timestamp"], reverse=True)
    else:
        cases = sorted(cases, key=lambda c: c["timestamp"])

    st.markdown("---")
    st.markdown("#### Priority Radar")
    st.caption("Each point is a case. Position reflects review priority and model confidence.")
    if cases:
        priority_radar_chart(cases)
    else:
        st.caption("No cases to visualize with current filters.")

    st.markdown("---")
    render_priority_legend()

    st.markdown(f"#### Queue ({len(cases)} cases)")
    st.caption("Open View Case on any card below to inspect it.")
    if not cases:
        render_empty_state("No items are currently awaiting review.")
    else:
        for c in cases:
            pr = PRIORITY_META.get(c["priority"], PRIORITY_META["Low"])
            pred = VERDICT_META.get(c["prediction"], VERDICT_META["Uncertain"])
            status = STATUS_META.get(c["review_status"], STATUS_META["Pending"])

            with st.container(key=f"case_card_{c['case_id']}"):
                left, right = st.columns([58, 42], gap="medium")
                with left:
                    st.markdown(
                        f"""
                        <div class="tl-case-id">{c['case_id']}</div>
                        <div class="tl-case-title">{c['title']}</div>
                        <div class="tl-case-source">Source: {c['source']}</div>
                        """,
                        unsafe_allow_html=True,
                    )
                with right:
                    st.markdown(
                        f"""
                        <div class="tl-case-right-row">
                            <span class="tl-badge {pr['class']}">{pr['emoji']} {c['priority']} Priority</span>
                        </div>
                        <div class="tl-case-right-row">
                            <span class="tl-badge {pred['badge']}">{pred['emoji']} {c['prediction']}</span>
                        </div>
                        <div class="tl-case-right-row tl-case-confidence">Confidence {c['confidence']*100:.1f}%</div>
                        <div class="tl-case-right-row">
                            <span class="tl-badge {status['class']}">{status['emoji']} {c['review_status']}</span>
                            <span class="tl-case-time">• {c['timestamp']}</span>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
                    with st.container(key=f"case_viewbtn_{c['case_id']}"):
                        col1, col2, col3 = st.columns([2, 1, 1])
                        with col1:
                            clicked = st.button("View Case →", key=f"open_{c['case_id']}", use_container_width=True)
                        with col2:
                            if st.button("✓ Review Done", key=f"done_{c['case_id']}",
                                         use_container_width=True):
                                if mark_review_done(c["case_id"]):
                                    set_flash(f"✓ Case {c['case_id']} marked as reviewed and moved to History.")
                                    st.rerun()
                                else:
                                    st.error("Could not update this case.")
                        with col3:
                            if st.button("🗑️ Delete", key=f"delete_{c['case_id']}", use_container_width=True):
                                if delete_case(c["case_id"]):
                                    set_flash(f"🗑️ Case {c['case_id']} deleted.")
                                    st.rerun()
                                else:
                                    st.error("Could not delete this case.")
            if clicked:
                st.session_state.selected_case = c["case_id"]
                st.session_state.case_origin_page = "Review Queue"
                st.session_state.current_page = "Review Case"
                st.rerun()
