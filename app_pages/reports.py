from datetime import datetime

import streamlit as st

from components.cards import render_empty_state
from components.header import render_header
from csv_to_frontend import get_all_cases, get_case_by_id
from utils.export import export_case_detail_pdf_bytes, export_csv_bytes, export_pdf_bytes


def render():
    render_header("Reports", "Generate case-level and batch reports")

    st.markdown("#### Individual Case Report")
    cases = get_all_cases()
    ids = [c["case_id"] for c in cases]
    selected = st.selectbox("Select Case", ids, key="report_case_select")
    case = get_case_by_id(selected)

    st.download_button(
        "⬇ Generate PDF",
        data=export_case_detail_pdf_bytes(case),
        file_name=f"truthlens_case_{case['case_id'].strip('#')}.pdf",
        mime="application/pdf",
        key="gen_case_pdf",
    )

    with st.expander("Preview Report"):
        st.markdown(f"""
        **TruthLens Analysis Report**

        - **Case ID:** {case['case_id']}
        - **Input content:** {case['text'][:160]}...
        - **Model Prediction (original):** {case['prediction']}
        - **Confidence:** {case['confidence']*100:.1f}%
        - **Review Priority:** {case['priority']}
        - **Source Profile:** {case['source']} ({case['source_credibility']*100:.0f}% historical credibility)
        - **Explanation:** {', '.join(e['feature'] for e in case['explanation'])}
        - **Linguistic Signals:** Sentiment {case['sentiment']}, Subjectivity {case['subjectivity']}
        - **Review Status:** {case['review_status']}
        - **Reviewer Opinion:** {case['reviewer_label'] or 'Not yet reviewed'}
        - **Reviewer Note:** {case['reviewer_note'] or '—'}
        - **Timestamp:** {case['timestamp']}
        """)

    st.markdown("---")
    st.markdown("#### Batch Report")
    st.selectbox("Select Dataset", ["Most Recent Batch Upload", "No other datasets available (prototype)"])

    batch = st.session_state.get("batch_result")
    c1, c2 = st.columns(2)
    if batch:
        rows = batch["rows"]
        with c1:
            st.download_button(
                "⬇ Generate PDF", data=export_pdf_bytes(rows, title="TruthLens — Batch Report"),
                file_name=f"truthlens_batch_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf",
                mime="application/pdf", key="gen_batch_pdf",
            )
        with c2:
            st.download_button(
                "⬇ Download CSV", data=export_csv_bytes(rows),
                file_name=f"truthlens_batch_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                mime="text/csv", key="gen_batch_csv",
            )
    else:
        c1.button("⬇ Generate PDF", key="gen_batch_pdf_disabled", disabled=True)
        c2.button("⬇ Download CSV", key="gen_batch_csv_disabled", disabled=True)

    if not st.session_state.get("batch_result"):
        render_empty_state("Run an analysis to generate a report.")

    st.markdown("---")
    st.markdown("#### ⬇ Download All Data")
    st.caption(
        "Every case in the system, with the model's original prediction and the reviewer's "
        "opinion kept as separate fields — reviewer feedback never overwrites the model's prediction."
    )
    d1, d2 = st.columns(2)
    with d1:
        st.download_button(
            "⬇ All Cases (CSV)", data=export_csv_bytes(cases),
            file_name=f"truthlens_all_cases_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
            mime="text/csv", key="gen_all_csv", 
        )
    with d2:
        st.download_button(
            "⬇ All Cases (PDF)", data=export_pdf_bytes(cases),
            file_name=f"truthlens_all_cases_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf",
            mime="application/pdf", key="gen_all_pdf", 
        )
