"""
utils/export.py

"""

import io
from datetime import datetime

import pandas as pd


def cases_to_dataframe(cases):
    """Flatten case dicts into a table with model + reviewer fields kept separate."""
    rows = []
    for c in cases:
        rows.append({
            "Case ID": c.get("case_id", ""),
            "Title": c.get("title", ""),
            "Source": c.get("source", ""),
            "Timestamp": c.get("timestamp", ""),
            "Model Prediction (original)": c.get("prediction", ""),
            "Model Confidence (%)": round(c.get("confidence", 0) * 100, 1),
            "Review Priority": c.get("priority", ""),
            "Review Status": c.get("review_status", "Pending"),
            "Reviewer Opinion": c.get("reviewer_label") or "Not yet reviewed",
            "Reviewer Note": c.get("reviewer_note", "") or "",
        })
    return pd.DataFrame(rows)


def export_csv_bytes(cases):
    df = cases_to_dataframe(cases)
    buf = io.StringIO()
    df.to_csv(buf, index=False)
    return buf.getvalue().encode("utf-8")


def _pdf_table_doc(df, title, subtitle=None):
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import (Paragraph, SimpleDocTemplate, Spacer,
                                     Table, TableStyle)

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=landscape(A4),
                             topMargin=28, bottomMargin=28, leftMargin=28, rightMargin=28)
    styles = getSampleStyleSheet()
    elements = [Paragraph(title, styles["Title"])]
    if subtitle:
        elements.append(Paragraph(subtitle, styles["Normal"]))
    elements.append(Paragraph(
        f"Generated {datetime.now().strftime('%Y-%m-%d %H:%M')} · Reviewer feedback is stored "
        f"separately from the model's original prediction and never overwrites it.",
        styles["Italic"],
    ))
    elements.append(Spacer(1, 12))
    if df is None or len(df.columns) == 0:
        elements.append(
            Paragraph(
                "No cases available to export.",
                styles["BodyText"]
            )
    )
        doc.build(elements)
        return buf.getvalue()
    data = [list(df.columns)] + df.astype(str).values.tolist()
    table = Table(data, repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#be185d")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTSIZE", (0, 0), (-1, -1), 6.8),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#d6d3d1")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#faf5ff")]),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
    ]))
    elements.append(table)
    doc.build(elements)
    return buf.getvalue()


def export_pdf_bytes(cases, title="TruthLens — All Cases Export", subtitle=None):
    df = cases_to_dataframe(cases)
    return _pdf_table_doc(df, title, subtitle)


def export_case_detail_pdf_bytes(case):
    """Single-case detail report (used by the Reports page)."""
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, topMargin=36, bottomMargin=36)
    styles = getSampleStyleSheet()
    elements = [
        Paragraph("TruthLens Analysis Report", styles["Title"]),
        Paragraph(f"Case {case['case_id']} — {case['title']}", styles["Heading2"]),
        Paragraph(f"Generated {datetime.now().strftime('%Y-%m-%d %H:%M')}", styles["Italic"]),
        Spacer(1, 10),
    ]

    rows = [
        ["Source", case.get("source", "—")],
        ["Timestamp", case.get("timestamp", "—")],
        ["Model Prediction (original)", case.get("prediction", "—")],
        ["Model Confidence", f"{case.get('confidence', 0) * 100:.1f}%"],
        ["Review Priority", case.get("priority", "—")],
        ["Source Credibility", f"{case.get('source_credibility', 0) * 100:.0f}%"],
        ["Explanation Signals", ", ".join(e["feature"] for e in case.get("explanation", []))],
        ["Sentiment / Subjectivity", f"{case.get('sentiment', '—')} / {case.get('subjectivity', '—')}"],
        ["Review Status", case.get("review_status", "Pending")],
        ["Reviewer Opinion", case.get("reviewer_label") or "Not yet reviewed"],
        ["Reviewer Note", case.get("reviewer_note") or "—"],
    ]
    table = Table([["Field", "Value"]] + rows, colWidths=[160, 340])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#be185d")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTSIZE", (0, 0), (-1, -1), 8.5),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#d6d3d1")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#faf5ff")]),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    elements.append(table)
    elements.append(Spacer(1, 10))
    elements.append(Paragraph("Full content:", styles["Heading4"]))
    elements.append(Paragraph(case.get("text", ""), styles["Normal"]))
    doc.build(elements)
    return buf.getvalue()
