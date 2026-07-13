"""
dashboard/asha_worker.py
-------------------------
ASHA Worker dashboard: registers mothers, records vitals (triggers the
AI risk model), sees a priority list sorted by risk, and manages
referrals. Every save here is immediately visible to the Doctor / PHC
/ Mother's own dashboard.
"""

from __future__ import annotations

from datetime import date

import streamlit as st

from ai import groq_client
from ai.risk_model import RiskAssessment
from dashboard.common import render_alert_banner, render_dashboard_header, render_sidebar
from services import data_service
from utils.session import current_user
from utils.ui import ai_badge, ai_status_panel, glass_card_close, glass_card_open, risk_badge, soft_divider
from utils.wizard import wizard_nav, wizard_progress, wizard_reset, wizard_step


def render_asha_dashboard() -> None:
    user = current_user()
    active = render_sidebar()
    render_alert_banner("asha")

    if active == "Dashboard":
        _overview()
    elif active == "My Mothers":
        _my_mothers()
    elif active == "New Assessment":
        _new_assessment()
    elif active == "Priority List":
        _priority_list()
    elif active == "Referrals":
        _referrals()
    else:
        _settings()


def _settings() -> None:
    render_dashboard_header("Settings", "AI connection status for this device.")
    ai_status_panel()


def _overview() -> None:
    summary = data_service.village_summary()
    render_dashboard_header("ASHA Worker Dashboard", "Erumaiyur village · assigned mothers overview")

    cols = st.columns(4)
    stats = [
        ("Mothers", summary["total_mothers"]), ("Pregnant", summary["pregnant"]),
        ("Pending Referrals", summary["pending_referrals"]), ("Open Alerts", summary["open_alerts"]),
    ]
    for col, (label, value) in zip(cols, stats):
        with col:
            st.markdown(f'<div class="glass-card stat-card"><div class="stat-value">{value}</div>'
                         f'<div class="stat-label">{label}</div></div>', unsafe_allow_html=True)

    soft_divider()
    st.markdown("#### Risk Distribution")
    rc = summary["risk_counts"]
    cols2 = st.columns(4)
    for col, level in zip(cols2, ["Low", "Moderate", "High", "Critical"]):
        with col:
            glass_card_open()
            st.markdown(risk_badge(level), unsafe_allow_html=True)
            st.markdown(f"### {rc.get(level, 0)}")
            glass_card_close()

    soft_divider()
    mothers = data_service.list_mothers()
    referrals = data_service.list_referrals()
    with st.spinner("AI is generating village insights…"):
        insights = groq_client.phc_village_insights(summary, mothers, referrals)
    glass_card_open()
    st.markdown(ai_badge(insights["ai_generated"]), unsafe_allow_html=True)
    st.markdown("**AI Village Insights**")
    st.write(insights["district_summary"])
    st.markdown(f"**Focus areas:** {', '.join(insights['high_risk_hotspots']) or '—'}")
    st.write(insights["operational_insights"])
    glass_card_close()


def _my_mothers() -> None:
    render_dashboard_header("My Mothers", "All mothers registered under your village.")
    mothers = data_service.list_mothers()

    with st.expander("➕ Register a new mother"):
        c1, c2 = st.columns(2)
        with c1:
            name = st.text_input("Full name", key="reg_name")
            age = st.number_input("Age", 15, 50, 24, key="reg_age")
            phone = st.text_input("Phone number", key="reg_phone")
        with c2:
            village = st.text_input("Village", value="Erumaiyur", key="reg_village")
            gravida = st.number_input("Pregnancy number (gravida)", 1, 10, 1, key="reg_gravida")
            lmp = st.date_input("Last menstrual period (LMP)", key="reg_lmp")
        prev_miscarriage = st.checkbox("Previous miscarriage on record", key="reg_miscarriage")
        if st.button("Register Mother", key="reg_submit"):
            data_service.register_mother({
                "name": name, "age": age, "phone": phone, "village": village,
                "gravida": gravida, "lmp": str(lmp), "previous_miscarriage": prev_miscarriage,
                "asha_id": "ASHA01", "doctor_id": "DOC01",
            })
            st.success(f"{name} registered — visible to Doctor and PHC immediately.")
            st.rerun()

    for m in mothers:
        latest = data_service.latest_assessment(m["id"])
        week = data_service.pregnancy_week(m)
        glass_card_open()
        st.markdown(f"**{m['name']}** ({m['age']}) · {m['village']} · Week {week if m.get('status')=='pregnant' else '—'}")
        st.markdown(risk_badge(latest["risk_level"]) if latest else risk_badge("Low"), unsafe_allow_html=True)
        glass_card_close()


_AA_FIELD_DEFAULTS = {
    "aa_systolic": 118, "aa_diastolic": 76, "aa_weight": 58.0, "aa_height": 158.0,
    "aa_sugar": 95, "aa_hb": 11.5, "aa_symptoms": [],
}


def _new_assessment() -> None:
    render_dashboard_header("New Assessment", "Record vitals — the AI will score risk and explain why.")
    mothers = data_service.list_mothers()
    if not mothers:
        st.info("Register a mother first under 'My Mothers'.")
        return

    # Bugfix: same class of issue as the pregnant-woman wizard -- the
    # Review step and the "finish" handler read these keys regardless of
    # which step last drew their widgets. setdefault() guarantees every
    # key exists no matter which step is active, eliminating the
    # AttributeError/KeyError crash reported for this page.
    for _key, _default in _AA_FIELD_DEFAULTS.items():
        st.session_state.setdefault(_key, _default)

    options = {f"{m['name']} ({m['id']})": m["id"] for m in mothers}
    selected_label = st.selectbox("Select mother", list(options.keys()), key="asha_assess_mother")
    mother_id = options[selected_label]

    steps = ["Vitals", "Blood Work", "Symptoms", "Review & Submit"]
    wizard_progress("asha_assess", steps)
    step = wizard_step("asha_assess")

    if step == 0:
        glass_card_open()
        st.number_input("Systolic BP (mmHg)", 60, 220, 118, key="aa_systolic")
        st.number_input("Diastolic BP (mmHg)", 40, 140, 76, key="aa_diastolic")
        st.number_input("Weight (kg)", 30.0, 150.0, 58.0, key="aa_weight")
        st.number_input("Height (cm)", 130.0, 190.0, 158.0, key="aa_height")
        glass_card_close()
    elif step == 1:
        glass_card_open()
        st.number_input("Blood Sugar (mg/dL)", 40, 400, 95, key="aa_sugar")
        st.number_input("Hemoglobin (g/dL)", 4.0, 18.0, 11.5, step=0.1, key="aa_hb")
        glass_card_close()
    elif step == 2:
        glass_card_open()
        st.multiselect(
            "Symptoms observed / reported",
            ["Mild nausea", "Mild fatigue", "Back pain", "Mild swelling in feet",
             "Severe headache", "Blurred vision", "Swelling in hands/face",
             "Reduced fetal movement", "Vaginal bleeding", "High fever", "Severe abdominal pain"],
            key="aa_symptoms",
        )
        glass_card_close()
    else:
        glass_card_open()
        st.write(f"BP: {st.session_state.aa_systolic}/{st.session_state.aa_diastolic} mmHg")
        st.write(f"Sugar: {st.session_state.aa_sugar} mg/dL · Hb: {st.session_state.aa_hb} g/dL")
        st.write(f"Symptoms: {', '.join(st.session_state.get('aa_symptoms', [])) or 'None'}")
        glass_card_close()

    action = wizard_nav("asha_assess", len(steps), on_finish_label="Submit Assessment")
    if action == "finish":
        vitals = {
            "systolic": st.session_state.aa_systolic, "diastolic": st.session_state.aa_diastolic,
            "weight_kg": st.session_state.aa_weight, "height_cm": st.session_state.aa_height,
            "sugar_mg_dl": st.session_state.aa_sugar, "hemoglobin": st.session_state.aa_hb,
            "symptoms": [s.lower() for s in st.session_state.get("aa_symptoms", [])],
        }
        result = data_service.record_assessment(mother_id, vitals, recorded_by="ASHA Worker")
        wizard_reset("asha_assess")
        st.success("Assessment saved — visible to the mother, Doctor and PHC immediately.")
        st.markdown(risk_badge(result["risk_level"]), unsafe_allow_html=True)
        for f in result["risk_factors"]:
            st.markdown(f"- {f}")
        if result["risk_level"] in ("High", "Critical"):
            st.warning("A referral and alert were created automatically for this High/Critical result.")

        rule_result = RiskAssessment(
            score=result["risk_score"], level=result["risk_level"],
            factors=result["risk_factors"], recommendation=result["recommendation"],
            referral_urgency=result.get("referral_urgency", "Routine"),
        )
        mother = data_service.get_mother(mother_id)
        with st.spinner("AI is drafting the visit summary…"):
            ai = groq_client.asha_visit_summary(mother, vitals, rule_result)

        glass_card_open()
        st.markdown(ai_badge(ai["ai_generated"]), unsafe_allow_html=True)
        st.markdown("**AI Visit Summary**")
        st.write(ai["visit_summary"])
        st.markdown(f"**Priority / Urgency:** {ai['urgency']}")
        if ai["missing_data"]:
            st.markdown("**Missing health data flagged by AI:** " + ", ".join(ai["missing_data"]))
        st.markdown(f"**Recommended follow-up interval:** {ai['follow_up_interval']}")
        st.markdown("**AI Field Notes:**")
        st.caption(ai["ai_visit_notes"])
        glass_card_close()


def _priority_list() -> None:
    render_dashboard_header("AI Risk Priority List", "Mothers sorted by their latest risk score, highest first.")
    mothers = data_service.list_mothers()
    rows = []
    for m in mothers:
        latest = data_service.latest_assessment(m["id"])
        rows.append((m, latest))
    rows.sort(key=lambda r: (r[1]["risk_score"] if r[1] else -1), reverse=True)

    for m, latest in rows:
        glass_card_open()
        cols = st.columns([3, 1])
        with cols[0]:
            st.markdown(f"**{m['name']}** · {m['village']}")
            if latest:
                st.caption(f"Score {latest['risk_score']}/100 · assessed {latest['date']}")
            else:
                st.caption("No assessment yet")
        with cols[1]:
            st.markdown(risk_badge(latest["risk_level"]) if latest else risk_badge("Low"), unsafe_allow_html=True)
        glass_card_close()


def _referrals() -> None:
    render_dashboard_header("Referrals", "Referrals generated automatically from High/Critical assessments.")
    referrals = data_service.list_referrals()
    if not referrals:
        st.info("No referrals yet.")
        return
    for r in referrals:
        mother = data_service.get_mother(r["mother_id"])
        glass_card_open()
        st.markdown(f"**{mother['name']}** · {r['date']} · {risk_badge(r['risk_level'])}", unsafe_allow_html=True)
        st.write(f"**Recommended facility:** {r['recommended_facility']}")
        st.write(f"**Urgency:** {r['urgency']} &nbsp;·&nbsp; **Status:** {r['status']}")
        with st.expander("Reasons"):
            for reason in r["reasons"]:
                st.markdown(f"- {reason}")
        glass_card_close()
