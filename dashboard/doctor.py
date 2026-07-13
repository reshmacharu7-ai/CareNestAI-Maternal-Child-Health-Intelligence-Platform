"""
dashboard/doctor.py
--------------------
Doctor dashboard: sees mothers referred by ASHA workers, reviews the
AI risk summary and vitals trend, and downloads/updates the referral.
"""

from __future__ import annotations

import streamlit as st

from ai import groq_client
from dashboard.common import render_alert_banner, render_dashboard_header, render_sidebar
from graphs.trend_charts import trend_figure
from services import data_service
from services.pdf_service import build_referral_pdf
from utils.ui import ai_badge, ai_status_panel, glass_card_close, glass_card_open, risk_badge, soft_divider


def render_doctor_dashboard() -> None:
    active = render_sidebar()
    render_alert_banner("doctor")

    if active == "Dashboard":
        _overview()
    elif active == "Referred Mothers":
        _referred_mothers()
    elif active == "Case Review":
        _case_review()
    elif active == "Referral PDFs":
        _referral_pdfs()
    else:
        _settings()


def _settings() -> None:
    render_dashboard_header("Settings", "AI connection status for this device.")
    ai_status_panel()


def _overview() -> None:
    summary = data_service.village_summary()
    render_dashboard_header("Doctor Dashboard", "Dr. Anand Kumar · Erumaiyur PHC")
    cols = st.columns(4)
    stats = [
        ("Total Mothers", summary["total_mothers"]), ("Pending Referrals", summary["pending_referrals"]),
        ("Open Alerts", summary["open_alerts"]), ("High/Critical", summary["risk_counts"]["High"] + summary["risk_counts"]["Critical"]),
    ]
    for col, (label, value) in zip(cols, stats):
        with col:
            st.markdown(f'<div class="glass-card stat-card"><div class="stat-value">{value}</div>'
                         f'<div class="stat-label">{label}</div></div>', unsafe_allow_html=True)

    soft_divider()
    st.markdown("#### Recent Activity")
    from data.store import recent_activity
    for entry in recent_activity(6):
        st.caption(f"{entry['time']} — {entry['message']}")


def _referred_mothers() -> None:
    render_dashboard_header("Referred Mothers", "All mothers with a pending or reviewed referral.")
    referrals = data_service.list_referrals()
    if not referrals:
        st.info("No referrals yet.")
        return
    for r in referrals:
        mother = data_service.get_mother(r["mother_id"])
        glass_card_open()
        cols = st.columns([3, 1])
        with cols[0]:
            st.markdown(f"**{mother['name']}** · {mother['village']} · referred {r['date']}")
            st.caption(f"By {r['created_by']} · {r['urgency']}")
        with cols[1]:
            st.markdown(risk_badge(r["risk_level"]), unsafe_allow_html=True)
        if r["status"] != "Reviewed":
            if st.button("Mark as Reviewed", key=f"review_{r['id']}"):
                data_service.update_referral_status(r["id"], "Reviewed")
                st.rerun()
        else:
            st.success("Reviewed")
        glass_card_close()


def _case_review() -> None:
    render_dashboard_header("Case Review", "Full AI summary and vitals trend for a mother.")
    mothers = data_service.list_mothers()
    options = {f"{m['name']} ({m['id']})": m["id"] for m in mothers}
    label = st.selectbox("Select mother", list(options.keys()), key="doc_case_mother")
    mother = data_service.get_mother(options[label])
    latest = data_service.latest_assessment(mother["id"])

    if not latest:
        st.info("No assessment recorded for this mother yet.")
        return

    glass_card_open()
    st.markdown(risk_badge(latest["risk_level"]), unsafe_allow_html=True)
    st.write(f"**Score:** {latest['risk_score']}/100 · **Week:** {latest['week']} · **Date:** {latest['date']}")
    st.markdown("**AI reasoning:**")
    for f in latest["risk_factors"]:
        st.markdown(f"- {f}")
    st.info(latest["recommendation"])
    glass_card_close()

    trend = data_service.trend_data(mother["id"])

    with st.spinner("AI is preparing the case summary…"):
        ai = groq_client.doctor_case_summary(mother, latest, trend)
    glass_card_open()
    st.markdown(ai_badge(ai["ai_generated"]), unsafe_allow_html=True)
    st.markdown("**AI Case Summary**")
    st.write(ai["case_summary"])
    st.markdown("**Clinical Highlights:**")
    for h in ai["clinical_highlights"]:
        st.markdown(f"- {h}")
    st.markdown(f"**Suggested Follow-up:** {ai['suggested_follow_up']}")
    st.markdown(f"**Suggested Investigations:** {ai['suggested_investigations']}")
    st.markdown("**Patient-friendly Explanation:**")
    st.info(ai["patient_friendly_explanation"])
    glass_card_close()
    if len(trend["dates"]) > 1:
        c1, c2 = st.columns(2)
        with c1:
            st.plotly_chart(trend_figure(trend, "systolic"), use_container_width=True)
        with c2:
            st.plotly_chart(trend_figure(trend, "risk_score", color="#FB7185"), use_container_width=True)


def _referral_pdfs() -> None:
    render_dashboard_header("Referral PDFs", "Generate a downloadable referral summary.")
    referrals = data_service.list_referrals()
    if not referrals:
        st.info("No referrals yet.")
        return
    options = {f"{data_service.get_mother(r['mother_id'])['name']} · {r['date']}": r for r in referrals}
    label = st.selectbox("Select referral", list(options.keys()), key="doc_pdf_referral")
    referral = options[label]
    mother = data_service.get_mother(referral["mother_id"])
    assessment = data_service.latest_assessment(mother["id"])

    if st.button("📄 Generate Referral PDF", key="gen_pdf"):
        with st.spinner("AI is writing the referral summary…"):
            ai_summary = groq_client.referral_pdf_summary(mother, assessment, referral)
        pdf_bytes = build_referral_pdf(mother, assessment, referral, ai_summary=ai_summary)
        st.download_button(
            "⬇️ Download PDF", data=pdf_bytes,
            file_name=f"CareNestAI_Referral_{mother['name'].replace(' ', '_')}.pdf",
            mime="application/pdf",
        )
