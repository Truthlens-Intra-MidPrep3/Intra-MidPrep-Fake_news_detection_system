from datetime import datetime

import streamlit as st

from csv_to_frontend import get_all_cases
from utils.export import export_csv_bytes, export_pdf_bytes

NAV_MAIN = [
    ("Analyze", "🔎"),
    ("Review Queue", "🚨"),
    ("Review Case", "📄"),
    ("History", "🗂️"),
    ("Reports", "📑"),
]

NAV_SYSTEM = [
    ("Settings", "⚙️"),
]


@st.dialog("Exit TruthLens?")
def _exit_dialog():
    stage = st.session_state.get("_exit_stage", "ask")

    if stage == "ask":
        st.warning("⚠️ Any changes made in this session will **not be saved** once you close or leave the app.")
        st.markdown("Would you like to save your data before exiting?")
        c1, c2 = st.columns(2)
        with c1:
            if st.button("✅ Yes, save my data", key="exit_yes", type="primary"):
                st.session_state["_exit_stage"] = "save"
                st.rerun()
        with c2:
            if st.button("🚪 No, exit without saving", key="exit_no"):
                st.session_state["_exit_stage"] = "goodbye"
                st.rerun()

    elif stage == "save":
        cases = get_all_cases()
        st.success("Choose a format to download everything analyzed and reviewed in this session:")
        d1, d2 = st.columns(2)
        with d1:
            st.download_button(
                "⬇ Save as CSV", data=export_csv_bytes(cases),
                file_name=f"truthlens_backup_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                mime="text/csv", key="exit_dl_csv",
            )
        with d2:
            st.download_button(
                "⬇ Save as PDF", data=export_pdf_bytes(cases),
                file_name=f"truthlens_backup_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf",
                mime="application/pdf", key="exit_dl_pdf",
            )
        st.caption("Once your download finishes, it's safe to close this browser tab.")
        if st.button("Close this dialog", key="exit_close_after_save"):
            st.session_state["_show_exit_dialog"] = False
            st.session_state["_exit_stage"] = "ask"
            st.rerun()

    else:  # goodbye
        st.info("No data was saved. You can now close this browser tab.")
        if st.button("Close this dialog", key="exit_close_no_save"):
            st.session_state["_show_exit_dialog"] = False
            st.session_state["_exit_stage"] = "ask"
            st.rerun()


def render_sidebar():
    with st.sidebar:
        st.markdown('<div class="tl-brand-title">TRUTHLENS</div>', unsafe_allow_html=True)
        st.markdown('<div class="tl-brand-sub">AI-Powered Misinformation Review</div>', unsafe_allow_html=True)

        st.markdown('<div class="tl-nav-section">Main</div>', unsafe_allow_html=True)
        for label, icon in NAV_MAIN:
            active = st.session_state.get("current_page") == label
            state = "active" if active else "inactive"
            with st.container(key=f"navbtn_{label.replace(' ', '_')}_{state}"):
                if st.button(f"{icon}  {label}", key=f"nav_{label}"):
                    st.session_state.current_page = label
                    st.rerun()

        st.markdown('<div class="tl-nav-section">System</div>', unsafe_allow_html=True)
        for label, icon in NAV_SYSTEM:
            active = st.session_state.get("current_page") == label
            state = "active" if active else "inactive"
            with st.container(key=f"navbtn_{label.replace(' ', '_')}_{state}"):
                if st.button(f"{icon}  {label}", key=f"nav_{label}"):
                    st.session_state.current_page = label
                    st.rerun()

        st.markdown('<div class="tl-footer">Session</div>', unsafe_allow_html=True)
        if st.button("🚪  Exit App", key="nav_exit"):
            st.session_state["_show_exit_dialog"] = True
            st.session_state["_exit_stage"] = "ask"
            st.rerun()
        st.caption("Closing or refreshing this tab will also ask your browser to confirm before leaving.")

        if st.session_state.get("_show_exit_dialog"):
            _exit_dialog()
