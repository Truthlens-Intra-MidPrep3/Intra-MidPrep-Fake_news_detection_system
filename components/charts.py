import plotly.graph_objects as go
import plotly.express as px
import streamlit as st
import pandas as pd

# Warm "plum & ember" palette — no green, blue, or teal anywhere.
COLOR_MAP = {"Likely Real": "#b45309", "Uncertain": "#db2777", "Likely Misinformation": "#be123c"}
PRIORITY_COLOR = {"High": "#be123c", "Medium": "#db2777", "Low": "#ca8a04"}
STATUS_COLOR = {"Pending": "#ca8a04", "Confirmed": "#b45309", "Dismissed": "#a8a29e", "Relabeled": "#0d9488"}
REVIEWED_COLOR = "#16a34a"  # matches the "Already Reviewed" legend dot


def prediction_distribution_chart(real, uncertain, misinfo):
    fig = go.Figure(data=[go.Pie(
        labels=["Likely Real", "Uncertain", "Likely Misinformation"],
        values=[real, uncertain, misinfo],
        marker=dict(colors=["#b45309", "#db2777", "#be123c"]),
        hole=0.55,
    )])
    fig.update_layout(margin=dict(t=10, b=10, l=10, r=10), height=300,
                       legend=dict(orientation="h", y=-0.15))
    st.plotly_chart(fig, width='stretch')


def review_status_chart(counts: dict):
    fig = go.Figure(data=[go.Bar(
        x=list(counts.keys()), y=list(counts.values()),
        marker_color=[STATUS_COLOR.get(k, "#78716c") for k in counts.keys()],
    )])
    fig.update_layout(margin=dict(t=10, b=10, l=10, r=10), height=300)
    st.plotly_chart(fig, width='stretch')


def priority_bar_chart(counts: dict):
    fig = go.Figure(data=[go.Bar(
        x=list(counts.keys()), y=list(counts.values()),
        marker_color=[PRIORITY_COLOR.get(k, "#78716c") for k in counts.keys()],
    )])
    fig.update_layout(margin=dict(t=10, b=10, l=10, r=10), height=300)
    st.plotly_chart(fig, width='stretch')


def activity_over_time_chart(days, values):
    fig = go.Figure(data=[go.Scatter(x=days, y=values, mode="lines+markers",
                                      line=dict(color="#0d9488", width=3))])
    fig.update_layout(margin=dict(t=10, b=10, l=10, r=10), height=300,
                       xaxis_title=None, yaxis_title="Items Analyzed")
    st.plotly_chart(fig, width='stretch')


def priority_radar_chart(cases):
    priority_x = {"Low": 1, "Medium": 2, "High": 3}
    df = pd.DataFrame([{
        "priority": c["priority"],
        "x": priority_x[c["priority"]] + (hash(c["case_id"]) % 100) / 300,
        "confidence": c["confidence"] * 100,
        "case_id": c["case_id"],
        "status": c["review_status"],
    } for c in cases])
    colors = []
    for _, row in df.iterrows():
        if row["status"] != "Pending":
            colors.append(REVIEWED_COLOR)
        else:
            colors.append(PRIORITY_COLOR.get(row["priority"], "#78716c"))
    fig = go.Figure(data=[go.Scatter(
        x=df["x"], y=df["confidence"], mode="markers",
        marker=dict(size=12, color=colors, line=dict(width=1, color="white")),
        text=df["case_id"], hovertemplate="Case %{text}<br>Confidence: %{y:.1f}%<extra></extra>",
    )])
    fig.update_layout(
        margin=dict(t=10, b=10, l=10, r=10), height=340,
        xaxis=dict(title="Review Priority / Risk Signal", tickvals=[1, 2, 3],
                   ticktext=["Low", "Medium", "High"]),
        yaxis=dict(title="Model Confidence (%)"),
    )
    st.plotly_chart(fig, width='stretch')


def source_history_donut(real_pct):
    fig = go.Figure(data=[go.Pie(
        labels=["Likely Real", "Likely Misinformation"],
        values=[real_pct, 1 - real_pct],
        marker=dict(colors=["#b45309", "#be123c"]),
        hole=0.6,
    )])
    fig.update_layout(margin=dict(t=0, b=0, l=0, r=0), height=220, showlegend=True,
                       legend=dict(orientation="h", y=-0.2))
    st.plotly_chart(fig, width='stretch')


def confusion_matrix_chart(cm):
    z = [[cm["tn"], cm["fp"]], [cm["fn"], cm["tp"]]]
    fig = go.Figure(data=go.Heatmap(
        z=z, x=["Predicted Real", "Predicted Misinfo"], y=["Actual Real", "Actual Misinfo"],
        colorscale="Reds", showscale=False, text=z, texttemplate="%{text}",
    ))
    fig.update_layout(margin=dict(t=10, b=10, l=10, r=10), height=320)
    st.plotly_chart(fig, width='stretch')


def confidence_spectrum(prob_misinfo):
    pct = prob_misinfo * 100
    fig = go.Figure()
    fig.add_shape(type="rect", x0=0, x1=50, y0=0, y1=1, fillcolor="#fef3c7", line_width=0)
    fig.add_shape(type="rect", x0=50, x1=100, y0=0, y1=1, fillcolor="#fecdd3", line_width=0)
    fig.add_trace(go.Scatter(x=[pct], y=[0.5], mode="markers+text",
                              marker=dict(size=18, color="#44403c", symbol="triangle-down"),
                              text=[f"{pct:.1f}%"], textposition="top center"))
    fig.update_layout(
        height=140, margin=dict(t=30, b=10, l=10, r=10),
        xaxis=dict(range=[0, 100], title="Likely Real ←  →  Likely Misinformation"),
        yaxis=dict(visible=False, range=[0, 1]),
    )
    st.plotly_chart(fig, width='stretch')
