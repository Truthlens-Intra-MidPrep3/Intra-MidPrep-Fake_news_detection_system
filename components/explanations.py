import streamlit as st
from .cards import render_progress_bar

SIGNAL_COLOR = {
    "Strong": "#be123c", "High": "#be123c", "Elevated": "#db2777",
    "Mixed": "#a16207", "Moderate": "#a16207", "Slight": "#eab308",
    "Weak": "#b45309", "Low": "#b45309",
}


def render_explanation_card(explanation):
    st.markdown("#### Why the model flagged this content")
    for item in explanation:
        color = SIGNAL_COLOR.get(item["label"], "#64748b")
        st.markdown(
            f"""
            <div class="tl-card">
                <div style="display:flex; justify-content:space-between;">
                    <b>{item['feature']}</b>
                    <span style="color:{color}; font-weight:700;">{item['label']}</span>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        render_progress_bar(item["score"] * 100, color)
        st.caption(item["text"])


def render_signal_breakdown(case):
    st.markdown("#### Signal Breakdown")
    
    explanations = {
        "Semantic Signal": "Measures the overall semantic coherence and relevance of the content. 'Mixed' indicates mixed signals about reliability.",
        "Sentiment": "Analyzes the emotional tone of the text. High sentiment can indicate emotional manipulation or bias.",
        "Subjectivity": "Measures how much the text is based on opinions vs. facts. Higher subjectivity may indicate bias or personal interpretation.",
        "Readability": "Indicates how easy the text is to understand. Very low readability can be a sign of poor quality content.",
        "Exclamation Ratio": "Counts the proportion of exclamation marks. High usage can indicate sensationalism or emotional appeals.",
        "Uppercase Ratio": "Measures the proportion of uppercase letters. High usage can indicate shouting or sensationalism."
    }
    
    cols = st.columns(3)
    fields = [
        ("Semantic Signal", case["semantic_signal"]),
        ("Sentiment", case["sentiment"]),
        ("Subjectivity", case["subjectivity"]),
        ("Readability", case["readability"]),
        ("Exclamation Ratio", case["exclamation_ratio"]),
        ("Uppercase Ratio", case["uppercase_ratio"]),
    ]
    
    # Create flip card CSS and HTML
    flip_css = """
    <style>
    .flip-card {
        background-color: transparent;
        width: 100%;
        height: 180px;
        perspective: 1000px;
    }
    .flip-card-inner {
        position: relative;
        width: 100%;
        height: 100%;
        transition: transform 0.6s;
        transform-style: preserve-3d;
    }
    .flip-card-front, .flip-card-back {
        position: absolute;
        width: 100%;
        height: 100%;
        backface-visibility: hidden;
        padding: 1rem;
        border-radius: 8px;
        display: flex;
        flex-direction: column;
        justify-content: center;
        align-items: center;
        text-align: center;
    }
    .flip-card-front {
        background-color: #ffffff;
        border: 1px solid #e7e2df;
        color: #262730;
        cursor: pointer;
    }
    .flip-card-back {
        background-color: #0d9488;
        color: white;
        transform: rotateY(180deg);
        font-size: 0.85rem;
        line-height: 1.4;
    }
    .flip-card:hover .flip-card-inner {
        transform: rotateY(180deg);
    }
    .flip-card-title {
        font-size: 0.75rem;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        font-weight: 700;
        margin-bottom: 0.5rem;
    }
    .flip-card-value {
        font-size: 1.2rem;
        font-weight: 700;
    }
    </style>
    """
    
    st.markdown(flip_css, unsafe_allow_html=True)
    
    for i, (label, value) in enumerate(fields):
        col = cols[i % 3]
        with col:
            flip_html = f"""
            <div class="flip-card">
                <div class="flip-card-inner">
                    <div class="flip-card-front">
                        <div class="flip-card-title">{label}</div>
                        <div class="flip-card-value">{value}</div>
                    </div>
                    <div class="flip-card-back">
                        <div>{explanations.get(label, "")}</div>
                    </div>
                </div>
            </div>
            """
            st.markdown(flip_html, unsafe_allow_html=True)


# Inline styles (not CSS classes) so the colours always show, whatever the theme/CSS cache does.
_HL_BASE = "padding:0.05rem 0.2rem; border-radius:4px; color:#1c1917;"
_HL_STYLE = {
    "semantic":   f"background:#fde047; {_HL_BASE}",                                   # yellow
    "linguistic": f"background:#c4b5fd; {_HL_BASE} font-weight:600;",                  # purple
    "claim":      f"background:#f9a8d4; {_HL_BASE}",                                   # pink
}


def _build_highlight_html(text, highlights, legacy_passages=None):
    """Paint highlight spans onto the ORIGINAL text (position based, HTML-escaped).
    Linguistic spans are painted after semantic ones so they stay visible inside a
    model-relevant sentence."""
    import html as _html
    n = len(text)
    kind = [None] * n
    reason = [""] * n
    spans = list(highlights or [])
    # legacy rows (old history data) only have text snippets
    for p in (legacy_passages or []):
        i = text.find(p.get("text", ""))
        if i >= 0 and p.get("text"):
            spans.append({"start": i, "end": i + len(p["text"]), "type": p.get("type", "semantic"), "reason": ""})
    for layer in ("semantic", "claim", "linguistic"):
        for h in spans:
            if h.get("type", "semantic") != layer:
                continue
            for i in range(max(0, h["start"]), min(n, h["end"])):
                kind[i], reason[i] = layer, h.get("reason", "")
    out, i = [], 0
    while i < n:
        j = i
        while j < n and kind[j] == kind[i] and reason[j] == reason[i]:
            j += 1
        chunk = _html.escape(text[i:j]).replace("\n", "<br>")
        if kind[i]:
            out.append(f'<span style="{_HL_STYLE[kind[i]]}" title="{_html.escape(reason[i])}">{chunk}</span>')
        else:
            out.append(chunk)
        i = j
    return "".join(out), any(k for k in kind)


def render_text_highlighting(case):
    with st.expander("🔍 Inspect Relevant Text"):
        st.markdown(
            f'<span style="{_HL_STYLE["semantic"]}">Model-relevant passage</span> &nbsp;&nbsp; '
            f'<span style="{_HL_STYLE["linguistic"]}">Linguistic signal</span> &nbsp;&nbsp; Normal text',
            unsafe_allow_html=True,
        )
        text = case["text"]
        html, found = _build_highlight_html(text, case.get("highlights"), case.get("highlighted_passages"))
        st.markdown(f'<div class="tl-card">{html}</div>', unsafe_allow_html=True)
        if not found:
            st.caption("No passage stood out: no sentence changed the model's result noticeably "
                       "and no shouting, exclamation or strongly emotional wording was found.")
        else:
            st.caption("Hover a highlight to see why it was marked.")


def render_supporting_vs_verified(case):
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("##### Model-Based Signals")
        items = "".join(f"<li>{e['label']} {e['feature'].lower()}</li>" for e in case["explanation"])
        st.markdown(
            f'<div class="tl-card"><ul>{items}<li>Source historical profile</li></ul></div>',
            unsafe_allow_html=True,
        )
    with col2:
        st.markdown("##### Verified Factual Evidence")
        st.markdown(
            '<div class="tl-card">No external fact-checking evidence has been supplied.<br><br>'
            '<span class="tl-note">Model predictions are not equivalent to verified fact-checking results.</span></div>',
            unsafe_allow_html=True,
        )
