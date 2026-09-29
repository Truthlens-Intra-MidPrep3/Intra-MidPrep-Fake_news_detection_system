from datetime import datetime

import streamlit as st

from components.cards import (
    priority_badge_html, prediction_badge_html, render_empty_state, status_badge_html,
    set_flash, show_flash,
)
from components.header import render_header
from csv_to_frontend import get_all_cases, delete_case
from utils.export import export_csv_bytes, export_pdf_bytes


def render():
    render_header(
        "Prediction & Review History",
        "Every analysed case (single and batch), with any reviewer decision recorded against the model's prediction",
    )

    show_flash()
    # History holds every analysed case; the Review Queue only holds cases sent to it.
    cases = get_all_cases()

    st.markdown(
        """
        <div class="tl-card">
        Each case below keeps the <b>model's original prediction</b> and the <b>reviewer's opinion</b>
        as two separate fields. Submitting a review never overwrites the model's prediction or any
        dataset label — it only records the reviewer's decision alongside it.
        </div>
        """,
        unsafe_allow_html=True,
    )

    f1, f2, f3 = st.columns(3)
    status_filter = f1.selectbox("Review Status", ["All", "Pending", "Confirmed", "Dismissed", "Relabeled"])
    pred_filter = f2.selectbox("Model Prediction", ["All", "Likely Real", "Uncertain", "Likely Misinformation"])
    search = f3.text_input("Search", placeholder="Case ID, title, source...")

    filtered = cases
    if status_filter != "All":
        filtered = [c for c in filtered if c["review_status"] == status_filter]
    if pred_filter != "All":
        filtered = [c for c in filtered if c["prediction"] == pred_filter]
    if search:
        s = search.lower()
        filtered = [c for c in filtered if s in c["title"].lower() or s in c["source"].lower() or s in c["case_id"].lower()]

    st.caption(f"Showing {len(filtered)} of {len(cases)} cases")
    st.markdown("---")

    if not filtered:
        render_empty_state("No cases yet. Every analysed case appears here." if not cases else "No cases match the current filters.")
    else:
        for c in filtered:
            if c["review_status"] == "Pending":
                reviewer_html = "<i style='color:#78716c;'>Not yet reviewed</i>"
            elif c["reviewer_label"]:
                reviewer_html = prediction_badge_html(c["reviewer_label"])
            else:
                reviewer_html = "<i style='color:#78716c;'>Flag dismissed</i>"
            st.markdown(
                f"""
                <div class="tl-card">
                    <div style="display:flex; justify-content:space-between; flex-wrap:wrap; gap:0.5rem; align-items:center;">
                        <div style="font-weight:800; color:#1c1917;">{c['case_id']} — {c['title']}</div>
                        {status_badge_html(c['review_status'])}
                    </div>
                    <div style="margin-top:0.6rem; display:flex; gap:2rem; flex-wrap:wrap;">
                        <div>
                            <div class="tl-card-title">Model Prediction (original)</div>
                            {prediction_badge_html(c['prediction'])}
                            <div style="font-size:0.8rem; color:#78716c; margin-top:0.2rem;">Confidence: {c['confidence']*100:.1f}%</div>
                        </div>
                        <div>
                            <div class="tl-card-title">Reviewer Opinion</div>
                            {reviewer_html}
                        </div>
                        <div>
                            <div class="tl-card-title">Priority</div>
                            {priority_badge_html(c['priority'])}
                        </div>
                    </div>
                    <div style="margin-top:0.6rem; color:#44403c; font-size:0.86rem;">
                        <b>Reviewer note:</b> {c['reviewer_note'] or '—'}
                    </div>
                    <div style="margin-top:0.25rem; color:#a8a29e; font-size:0.76rem;">
                        Source: {c['source']} &nbsp;•&nbsp; {c['timestamp']}{' &nbsp;•&nbsp; In Review Queue' if c['in_queue'] and c['review_status'] == 'Pending' else ''}
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            col1, col2 = st.columns(2)
            with col1:
                if st.button("Open case →", key=f"hist_open_{c['case_id']}", use_container_width=True):
                    st.session_state.selected_case = c["case_id"]
                    st.session_state.case_origin_page = "History"
                    st.session_state.current_page = "Review Case"
                    st.rerun()
            with col2:
                if st.button("🗑️ Delete", key=f"hist_delete_{c['case_id']}", use_container_width=True):
                    if delete_case(c["case_id"]):
                        set_flash(f"🗑️ Case {c['case_id']} deleted.")
                        st.rerun()
                    else:
                        st.error("Could not delete this case.")

    st.markdown("---")
    st.markdown("#### ⬇ Download All Data")
    st.caption(
        "Exports include every case's model prediction and reviewer opinion as separate fields — "
        "reviewer feedback never overwrites the model's original prediction."
    )
    dl1, dl2 = st.columns(2)
    with dl1:
        st.download_button(
            "⬇ Download All Cases (CSV)",
            data=export_csv_bytes(cases),
            file_name=f"truthlens_all_cases_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
            mime="text/csv",
            key="hist_dl_csv",
            
        )
    with dl2:
        st.download_button(
            "⬇ Download All Cases (PDF)",
            data=export_pdf_bytes(cases),
            file_name=f"truthlens_all_cases_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf",
            mime="application/pdf",
            key="hist_dl_pdf",
            
        )
