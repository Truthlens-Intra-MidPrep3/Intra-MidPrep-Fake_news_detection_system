import streamlit as st
from components.header import render_header


def render():
    render_header("Settings", "Prototype configuration")

    # Initialize session state for settings
    if "theme_selection" not in st.session_state:
        st.session_state.theme_selection = "Light"
    if "filter_selection" not in st.session_state:
        st.session_state.filter_selection = "Pending"
    if "confidence_display" not in st.session_state:
        st.session_state.confidence_display = "Percentage"
    if "show_responsible_use" not in st.session_state:
        st.session_state.show_responsible_use = True

    theme = st.selectbox(
        "Theme", 
        ["Light", "Dark"],
        index=0 if st.session_state.theme_selection == "Light" else 1,
        key="theme_setting"
    )
    if theme != st.session_state.theme_selection:
        st.session_state.theme_selection = theme
        st.rerun()

    filter_opt = st.selectbox(
        "Default Review Filter",
        ["Pending", "Confirmed", "Dismissed", "Relabeled", "All"],
        index=0
    )
    st.session_state.filter_selection = filter_opt

    conf_display = st.selectbox(
        "Confidence Display",
        ["Percentage", "Decimal"],
        index=0
    )
    st.session_state.confidence_display = conf_display

    show_notice = st.toggle("Show Responsible Use Notices", value=True)
    st.session_state.show_responsible_use = show_notice

    st.toggle("Prototype Mode", value=True, disabled=True,
              help="This build only supports Prototype Mode until backend integration is complete.")

    st.markdown("---")
    st.success(f"✓ Settings applied! Current theme: **{st.session_state.theme_selection}**")
