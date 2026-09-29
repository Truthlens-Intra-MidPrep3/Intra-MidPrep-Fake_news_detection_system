import streamlit as st
import streamlit.components.v1 as components
from csv_to_frontend import get_all_cases, get_case_by_id, mark_review_done, reopen_case
from components.cards import (
    set_flash, show_flash,
    render_empty_state, status_badge_html, prediction_badge_html,
    priority_badge_html, render_responsible_use_visible,
)
from components.explanations import (
    render_explanation_card, render_signal_breakdown,
    render_text_highlighting, render_supporting_vs_verified,
)
from components.review import (
    render_source_profile, render_review_controls,
    render_review_history, render_model_vs_human,
)


def render():
    origin = st.session_state.get("case_origin_page", "Review Queue")
    if st.button(f"⬅ Back to {origin}", key="case_explorer_back"):
        st.session_state.current_page = origin
        st.rerun()

    # Scroll the page back to the top — otherwise it opens wherever the
    # Review Queue happened to be scrolled to. Streamlit's own scroll
    # restoration can re-apply the old scroll position a moment after this
    # script first runs, so we keep re-forcing it to the top for a short
    # window rather than scrolling just once.
    components.html(
        """
        <script>
            (function() {
                function scrollToTop() {
                    const doc = window.parent.document;
                    const candidates = [
                        doc.scrollingElement,
                        doc.body,
                        doc.querySelector('section.main'),
                        doc.querySelector('[data-testid="stAppViewContainer"]'),
                        doc.querySelector('[data-testid="stMain"]'),
                        doc.querySelector('[data-testid="stAppViewBlockContainer"]'),
                    ];
                    candidates.forEach(function(el) {
                        if (!el) return;
                        if (typeof el.scrollTo === 'function') { el.scrollTo(0, 0); }
                        el.scrollTop = 0;
                    });
                    window.parent.scrollTo(0, 0);
                }
                scrollToTop();
                let tries = 0;
                const timer = setInterval(function() {
                    scrollToTop();
                    tries += 1;
                    if (tries > 15) { clearInterval(timer); }
                }, 40);
            })();
        </script>
        """,
        height=0,
    )

    show_flash()
    cases = get_all_cases()
    ids = [c["case_id"] for c in cases]

    if not ids:
        render_empty_state("Select a case from the Review Queue to inspect it.")
        return

    default_idx = ids.index(st.session_state.selected_case) if st.session_state.get("selected_case") in ids else 0
    selected = st.selectbox("Select Case", ids, index=default_idx)
    st.session_state.selected_case = selected
    case = get_case_by_id(selected)

    status_html = (
        '<span class="tl-badge tl-badge-pending">🟡 Pending Human Review</span>'
        if case["review_status"] == "Pending" else status_badge_html(case["review_status"])
    )

    st.markdown(
        f"""
        <div class="tl-card">
            <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:0.5rem;">
                <div>
                    <div style="font-size:0.76rem; text-transform:uppercase; letter-spacing:0.8px; color:#64748b; font-weight:700;">
                        You are reviewing this case
                    </div>
                    <div style="font-size:1.25rem; font-weight:800; color:#0f172a;">{case['case_id']} — {case['title']}</div>
                </div>
                {status_html}
            </div>
            <div style="margin-top:0.55rem; display:flex; align-items:center; gap:0.6rem; flex-wrap:wrap;">
                {prediction_badge_html(case['prediction'])}
                <span style="color:#475569;">Confidence: {case['confidence']*100:.1f}%</span>
                {priority_badge_html(case['priority'])}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    main_col, side_col = st.columns([2.2, 1])

    with main_col:
        with st.expander("💡 How to review this case"):
            st.markdown(
                """
1. Read the original content.
2. Check the model's prediction and confidence.
3. Inspect the explanation and relevant signals.
4. Review source information when available.
5. Make your own assessment.
6. Add a note explaining your decision.
                """
            )

        st.markdown("### ① Read the Content")
        st.markdown(f"**Title:** {case['title']}")
        st.markdown(f"**Source:** {case['source']}  |  **Author:** {case['author'] or 'Unknown'}")
        st.write(case["text"])

        st.markdown("---")
        st.markdown("### ② AI Assessment")
        st.markdown(
            f"""
            <div class="tl-card">
                <div class="tl-card-title">AI Assessment</div>
                {prediction_badge_html(case['prediction'])}
                <div style="margin-top:0.5rem; color:#475569;">
                    Confidence: <b>{case['confidence']*100:.1f}%</b>
                    &nbsp;•&nbsp; Review Priority: <b>{case['priority'].upper()}</b>
                </div>
                <div class="tl-note" style="margin-top:0.6rem;">
                    This is a model assessment and should be reviewed alongside the available
                    supporting information.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown("---")
        st.markdown("### ③ Understand Why")
        st.caption("Why did the model flag this?")
        render_explanation_card(case["explanation"])
        render_signal_breakdown(case)
        render_text_highlighting(case)

        st.markdown("---")
        st.markdown("### ④ Inspect Supporting Information")
        render_source_profile(case)
        with st.expander("Review History"):
            render_review_history(case)
            if case["review_status"] != "Pending":
                if st.button("↩️ Bring back to Review Queue", key=f"bringback_{case.get('case_id')}"):
                    if reopen_case(case["case_id"]):
                        set_flash(f"↩️ Case {case['case_id']} moved back to the Review Queue.")
                        st.rerun()
                    else:
                        st.error("Could not move this case back.")

        st.markdown("---")
        st.markdown("### ⑤ Make Your Decision")
        st.caption("Your decision is stored separately and never overwrites the model's original prediction.")
        render_review_controls(case, key_prefix="explorer")

        if st.button("✓ Review Done", key=f"explorer_done_{case['case_id']}",
                     disabled=case["review_status"] != "Pending",
                     help="Marks this case as Confirmed"):
            if mark_review_done(case["case_id"]):
                set_flash(f"✓ Case {case['case_id']} marked as reviewed and moved to History.")
                st.rerun()
            else:
                st.error("Could not update this case.")

        if case["review_status"] != "Pending":
            st.markdown("##### Model Prediction vs. Human Review")
            render_model_vs_human(case)

    with side_col:
        st.markdown(
            f"""
            <div class="tl-card">
                <div class="tl-card-title">Case Summary</div>
                <div style="font-size:1.1rem; font-weight:800; margin-bottom:0.5rem;">{case['case_id']}</div>
                <div style="margin-bottom:0.15rem; color:#64748b; font-size:0.76rem; text-transform:uppercase; font-weight:700;">Prediction</div>
                <div style="margin-bottom:0.5rem;">{prediction_badge_html(case['prediction'])}</div>
                <div style="margin-bottom:0.15rem; color:#64748b; font-size:0.76rem; text-transform:uppercase; font-weight:700;">Confidence</div>
                <div style="margin-bottom:0.5rem; color:#0f172a;">{case['confidence']*100:.1f}%</div>
                <div style="margin-bottom:0.15rem; color:#64748b; font-size:0.76rem; text-transform:uppercase; font-weight:700;">Priority</div>
                <div style="margin-bottom:0.5rem;">{priority_badge_html(case['priority'])}</div>
                <div style="margin-bottom:0.15rem; color:#64748b; font-size:0.76rem; text-transform:uppercase; font-weight:700;">Source</div>
                <div style="margin-bottom:0.5rem; color:#0f172a;">{case['source']}</div>
                <div style="margin-bottom:0.15rem; color:#64748b; font-size:0.76rem; text-transform:uppercase; font-weight:700;">Status</div>
                <div>{status_html}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.caption("This summary stays visible while you scroll through the review steps.")

    st.markdown("---")
    render_responsible_use_visible()
