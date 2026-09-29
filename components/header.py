import streamlit as st


def render_header(title, subtitle=""):
    st.markdown(
        f"""
        <div class="tl-header">
            <div style="display:flex; justify-content:space-between; align-items:flex-end;">
                <div>
                    <h2 style="margin-bottom:0;">{title}</h2>
                    <div style="color:#64748b; font-size:0.92rem;">{subtitle}</div>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
