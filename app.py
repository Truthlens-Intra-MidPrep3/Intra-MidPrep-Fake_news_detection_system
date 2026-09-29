"""
app.py — TruthLens frontend prototype entry point.

"""

import streamlit as st
import streamlit.components.v1 as components
from styles import CUSTOM_CSS
from components.sidebar import render_sidebar

st.set_page_config(
    page_title="TruthLens — AI-Powered Misinformation Review",
    page_icon="🛰️",
    layout="wide",
)

st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

# Persistent top masthead — stays visible even when the sidebar is collapsed.
st.markdown(
    """
    <div class="tl-masthead">
        <span class="tl-masthead-brand">TRUTHLENS</span>
        <span class="tl-masthead-sub">AI-Powered Misinformation Review</span>
    </div>
    """,
    unsafe_allow_html=True,
)

# ---- Session state defaults ----
defaults = {
    "current_page": "Analyze",
    "analysis_result": None,
    "selected_case": None,
    "case_origin_page": "Review Queue",
    "batch_uploaded": False,
    "batch_result": None,
    "filters": {},
    "_show_exit_dialog": False,
    "_exit_stage": "ask",
    "_beforeunload_injected": False,
    "theme_selection": "Light",
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

# Apply dark theme CSS if selected
if st.session_state.get("theme_selection") == "Dark":
    dark_theme_css = """
    <style>
    body, .stApp, [class*="st"] {
        background-color: #0e1117 !important;
        color: #e6edf3 !important;
    }
    .stApp {
        background: linear-gradient(135deg, #0d1117 0%, #161b22 100%);
    }
    p, div, span, label, h1, h2, h3, h4, h5, h6 {
        color: #e6edf3 !important;
    }
    .stTextInput > div > div > input,
    .stTextArea > div > div > textarea,
    .stSelectbox > div > div > select {
        background-color: #161b22 !important;
        color: #e6edf3 !important;
        border-color: #30363d !important;
    }
    [data-testid="stSidebar"] {
        background-color: #0d1117 !important;
    }
    .tl-card {
        background: #161b22 !important;
        border-color: #30363d !important;
    }
    </style>
    """
    st.markdown(dark_theme_css, unsafe_allow_html=True)

# Warn before the browser tab is actually closed or refreshed, since in-memory
# session data (analyses + reviews) is lost when that happens. Browsers only
# show their own generic confirmation text here for security reasons — they
# don't allow a page to supply custom wording or custom Yes/No buttons on
# this native dialog. The sidebar's "Exit App" button provides the fully
# custom Yes/No + save-to-CSV/PDF flow for that reason.
#
# Switching between TruthLens pages (Analyze, Review Queue, etc.) never
# leaves this browser tab — it's just a session_state change followed by
# st.rerun(), handled over the same websocket connection — so it should never
# trigger this warning on its own. 

if not st.session_state["_beforeunload_injected"]:
    components.html(
        """
        <script>
            (function () {
                var doc = window.parent.document;
                if (!doc.__tlBeforeUnloadBound) {
                    doc.__tlBeforeUnloadBound = true;
                    window.parent.addEventListener('beforeunload', function (e) {
                        e.preventDefault();
                        e.returnValue = '';
                    });
                }
            })();
        </script>
        """,
        height=0,
    )
    st.session_state["_beforeunload_injected"] = True

render_sidebar()

PAGE_MODULES = {
    "Analyze": "app_pages.analyze",
    "Review Queue": "app_pages.review_queue",
    "Review Case": "app_pages.case_explorer",
    "History": "app_pages.history",
    "Reports": "app_pages.reports",
    "Settings": "app_pages.settings",
}

import importlib

page = st.session_state.current_page
module_name = PAGE_MODULES.get(page, "app_pages.analyze")
module = importlib.import_module(module_name)
module.render()
