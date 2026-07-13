"""
graphs/trend_charts.py
-----------------------
AI Feature 8: Trend Analysis. Plotly figures for a mother's vitals over
time, styled to match the CareNest AI dark glassmorphism theme.
"""

from __future__ import annotations

import plotly.graph_objects as go

PAPER_BG = "rgba(0,0,0,0)"
PLOT_BG = "rgba(0,0,0,0)"
GRID_COLOR = "rgba(255,255,255,0.08)"
TEXT_COLOR = "#C7D2E0"
LINE_COLOR = "#22D3EE"
FILL_COLOR = "rgba(34, 211, 238, 0.12)"

FIELD_LABELS = {
    "systolic": ("Systolic BP", "mmHg"),
    "diastolic": ("Diastolic BP", "mmHg"),
    "sugar": ("Blood Sugar", "mg/dL"),
    "hemoglobin": ("Hemoglobin", "g/dL"),
    "weight": ("Weight", "kg"),
    "risk_score": ("Risk Score", "/100"),
}


def _base_layout(title: str, y_label: str) -> dict:
    return dict(
        title=dict(text=title, font=dict(size=15, color=TEXT_COLOR, family="Inter, sans-serif")),
        paper_bgcolor=PAPER_BG,
        plot_bgcolor=PLOT_BG,
        font=dict(color=TEXT_COLOR, family="Inter, sans-serif"),
        margin=dict(l=40, r=20, t=50, b=40),
        xaxis=dict(gridcolor=GRID_COLOR, showgrid=True, title="Date"),
        yaxis=dict(gridcolor=GRID_COLOR, showgrid=True, title=y_label),
        height=300,
    )


def trend_figure(trend: dict, field: str, color: str = LINE_COLOR) -> go.Figure:
    label, unit = FIELD_LABELS.get(field, (field, ""))
    dates = trend.get("dates", [])
    values = trend.get(field, [])
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=dates, y=values, mode="lines+markers", name=label,
        line=dict(color=color, width=3, shape="spline"),
        marker=dict(size=7, color=color),
        fill="tozeroy", fillcolor=FILL_COLOR,
    ))
    fig.update_layout(**_base_layout(f"{label} Over Time", unit))
    return fig


def summarize_trend(trend: dict) -> str:
    """Simple, explainable improving/worsening summary (no LLM needed)."""
    scores = [s for s in trend.get("risk_score", []) if s is not None]
    if len(scores) < 2:
        return "Not enough assessments yet to show a trend. Record another check-up to see how things are changing."
    delta = scores[-1] - scores[0]
    if delta <= -10:
        return f"Improving: risk score dropped from {scores[0]:.0f} to {scores[-1]:.0f} over {len(scores)} assessments."
    if delta >= 10:
        return f"Worsening: risk score rose from {scores[0]:.0f} to {scores[-1]:.0f} over {len(scores)} assessments — please prioritise a follow-up."
    return f"Stable: risk score has stayed close to {scores[-1]:.0f} across {len(scores)} assessments."
