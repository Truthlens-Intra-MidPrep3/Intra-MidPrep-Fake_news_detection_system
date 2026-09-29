import streamlit as st

VERDICT_META = {
    "Likely Real": {"emoji": "🟢", "class": "tl-verdict-real", "badge": "tl-badge-real"},
    "Uncertain": {"emoji": "🟡", "class": "tl-verdict-uncertain", "badge": "tl-badge-uncertain"},
    "Likely Misinformation": {"emoji": "🔴", "class": "tl-verdict-misinfo", "badge": "tl-badge-misinfo"},
}

PRIORITY_META = {
    "High": {"emoji": "🔴", "class": "tl-badge-high"},
    "Medium": {"emoji": "🟠", "class": "tl-badge-medium"},
    "Low": {"emoji": "🟡", "class": "tl-badge-low"},
}

STATUS_META = {
    "Pending": {"emoji": "🟡", "class": "tl-badge-pending"},
    "Confirmed": {"emoji": "🟢", "class": "tl-badge-confirmed"},
    "Dismissed": {"emoji": "⚪", "class": "tl-badge-dismissed"},
    "Relabeled": {"emoji": "🔵", "class": "tl-badge-relabeled"},
}


def set_flash(message, kind="success"):
    """Queue a message that is shown on the next run (st.rerun would otherwise wipe it)."""
    st.session_state["_flash"] = (kind, message)


def show_flash():
    flash = st.session_state.pop("_flash", None)
    if flash:
        getattr(st, flash[0], st.info)(flash[1])


def render_metric_card(label, value, help_text=None):
    st.metric(label, value, help=help_text)


def render_priority_badge(priority):
    meta = PRIORITY_META.get(priority, PRIORITY_META["Low"])
    st.markdown(
        f'<span class="tl-badge {meta["class"]}">{meta["emoji"]} {priority.upper()}</span>',
        unsafe_allow_html=True,
    )


def priority_badge_html(priority):
    meta = PRIORITY_META.get(priority, PRIORITY_META["Low"])
    return f'<span class="tl-badge {meta["class"]}">{meta["emoji"]} {priority}</span>'


def render_review_status(status):
    meta = STATUS_META.get(status, STATUS_META["Pending"])
    st.markdown(
        f'<span class="tl-badge {meta["class"]}">{meta["emoji"]} {status}</span>',
        unsafe_allow_html=True,
    )


def status_badge_html(status):
    meta = STATUS_META.get(status, STATUS_META["Pending"])
    return f'<span class="tl-badge {meta["class"]}">{meta["emoji"]} {status}</span>'


def prediction_badge_html(prediction):
    meta = VERDICT_META.get(prediction, VERDICT_META["Uncertain"])
    return f'<span class="tl-badge {meta["badge"]}">{meta["emoji"]} {prediction}</span>'


def render_prediction_card(result):
    """Large top-of-page verdict banner."""
    meta = VERDICT_META.get(result["prediction"], VERDICT_META["Uncertain"])
    st.markdown(
        f"""
        <div class="tl-verdict {meta['class']}">
            <div class="tl-verdict-label">{meta['emoji']} {result['prediction'].upper()}</div>
            <div class="tl-verdict-sub">Calibrated Confidence: {result['confidence']*100:.1f}%
                &nbsp;•&nbsp; Review Priority: {result['priority'].upper()}
                &nbsp;•&nbsp; Case {result['case_id']}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_case_card(case):
    meta = VERDICT_META.get(case["prediction"], VERDICT_META["Uncertain"])
    pr = PRIORITY_META.get(case["priority"], PRIORITY_META["Low"])
    st_ = STATUS_META.get(case["review_status"], STATUS_META["Pending"])
    st.markdown(
        f"""
        <div class="tl-card">
            <div style="display:flex; justify-content:space-between; align-items:center;">
                <div style="font-weight:700;">{case['case_id']} — {case['title']}</div>
                <div>{pr['emoji']} {case['priority']} &nbsp;|&nbsp; {st_['emoji']} {case['review_status']}</div>
            </div>
            <div style="margin-top:0.35rem; color:#475569; font-size:0.88rem;">
                {meta['emoji']} <b>{case['prediction']}</b> &nbsp;•&nbsp; Confidence {case['confidence']*100:.1f}%
                &nbsp;•&nbsp; Source: {case['source']} &nbsp;•&nbsp; {case['timestamp']}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_empty_state(message, icon="🗂️"):
    st.markdown(
        f'<div class="tl-empty"><div style="font-size:2rem;">{icon}</div>{message}</div>',
        unsafe_allow_html=True,
    )


def render_progress_bar(pct, color):
    st.markdown(
        f"""
        <div class="tl-bar-track">
            <div class="tl-bar-fill" style="width:{pct}%; background:{color};"></div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_responsible_use():
    with st.expander("⚠ Responsible Use"):
        st.markdown(
            """
This system provides **model-based risk assessments**, not definitive proof of whether a claim
is true or false. Results should be reviewed alongside reliable evidence and human judgment.

- Historical source credibility is a *supporting signal* and should not be treated as conclusive evidence.
- Results may be affected by incomplete metadata, unavailable propagation information, and dataset limitations.
            """
        )


def render_responsible_use_visible():
    """Same responsible-use messaging as render_responsible_use(), but always
    shown directly on the page instead of tucked behind a collapsed expander."""
    st.markdown("#### ⚠ Responsible Use")
    st.markdown(
        """
        <div class="tl-card">
        This system provides <b>model-based risk assessments</b>, not definitive proof of whether a claim
        is true or false. Results should be reviewed alongside reliable evidence and human judgment.
        <ul>
            <li>Historical source credibility is a <i>supporting signal</i> and should not be treated as conclusive evidence.</li>
            <li>Results may be affected by incomplete metadata, unavailable propagation information, and dataset limitations.</li>
        </ul>
        </div>
        """,
        unsafe_allow_html=True,
    )
