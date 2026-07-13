"""
dashboard/phc.py
-----------------
Primary Health Centre dashboard: incoming referrals queue and
village-wide statistics.
"""

from __future__ import annotations

import streamlit as st

from ai import groq_client
from dashboard.common import render_alert_banner, render_dashboard_header, render_sidebar
from services import data_service
from utils.ui import ai_badge, ai_status_panel, glass_card_close, glass_card_open, risk_badge, soft_divider


def render_phc_dashboard() -> None:
    active = render_sidebar()
    render_alert_banner("phc")

    if active == "Dashboard":
        _overview()
    elif active == "Incoming Referrals":
        _incoming_referrals()
    elif active == "Village Statistics":
        _village_stats()
    else:
        _settings()


def _settings() -> None:
    render_dashboard_header("Settings", "AI connection status for this device.")
    ai_status_panel()


def _overview() -> None:
    summary = data_service.village_summary()
    render_dashboard_header("Primary Health Centre — Erumaiyur", "Village-wide maternal & child health overview")
    cols = st.columns(4)
    stats = [
        ("Total Mothers", summary["total_mothers"]), ("Postpartum / Children", summary["total_children"]),
        ("Pending Referrals", summary["pending_referrals"]), ("Open Alerts", summary["open_alerts"]),
    ]
    for col, (label, value) in zip(cols, stats):
        with col:
            st.markdown(f'<div class="glass-card stat-card"><div class="stat-value">{value}</div>'
                         f'<div class="stat-label">{label}</div></div>', unsafe_allow_html=True)

    soft_divider()
    mothers = data_service.list_mothers()
    referrals = data_service.list_referrals()
    with st.spinner("AI is generating the district summary…"):
        insights = groq_client.phc_village_insights(summary, mothers, referrals)
    glass_card_open()
    st.markdown(ai_badge(insights["ai_generated"]), unsafe_allow_html=True)
    st.markdown("**AI District Summary**")
    st.write(insights["district_summary"])
    st.markdown(f"**High-risk hotspots:** {', '.join(insights['high_risk_hotspots']) or '—'}")
    st.markdown("**Operational insights:**")
    st.write(insights["operational_insights"])
    st.markdown("**Resource recommendations:**")
    st.write(insights["resource_recommendations"])
    glass_card_close()


def _incoming_referrals() -> None:
    render_dashboard_header("Incoming Referrals", "Priority queue, highest urgency first.")
    referrals = data_service.list_referrals()
    order = {"Critical": 0, "High": 1, "Moderate": 2, "Low": 3}
    referrals.sort(key=lambda r: order.get(r["risk_level"], 4))

    if not referrals:
        st.info("No referrals yet.")
        return

    for r in referrals:
        mother = data_service.get_mother(r["mother_id"])
        glass_card_open()
        st.markdown(f"**{mother['name']}** · {mother['village']} · {risk_badge(r['risk_level'])}", unsafe_allow_html=True)
        st.write(f"**Facility:** {r['recommended_facility']} &nbsp;·&nbsp; **Urgency:** {r['urgency']} &nbsp;·&nbsp; **Status:** {r['status']}")
        glass_card_close()


def _village_stats() -> None:
    render_dashboard_header("Village Statistics", "Risk distribution across all tracked mothers.")
    summary = data_service.village_summary()
    rc = summary["risk_counts"]

    soft_divider()
    cols = st.columns(4)
    for col, level in zip(cols, ["Low", "Moderate", "High", "Critical"]):
        with col:
            glass_card_open()
            st.markdown(risk_badge(level), unsafe_allow_html=True)
            st.markdown(f"### {rc.get(level, 0)}")
            glass_card_close()

    soft_divider()
    st.markdown("#### All Mothers")
    for m in data_service.list_mothers():
        latest = data_service.latest_assessment(m["id"])
        glass_card_open()
        st.markdown(f"**{m['name']}** · {m['status'].title()} · "
                     + (risk_badge(latest["risk_level"]) if latest else risk_badge("Low")), unsafe_allow_html=True)
        glass_card_close()
