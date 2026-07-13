"""
dashboard/pregnant_woman.py
----------------------------
Primary user dashboard. Covers: risk check-up (multi-step wizard),
pregnancy timeline, nutrition planner, child growth/immunization
tracking, trend charts, and the AI health companion chatbot.
"""

from __future__ import annotations

import streamlit as st

from ai import chatbot, child_growth, groq_client, nutrition, schedule
from dashboard.common import render_alert_banner, render_dashboard_header, render_sidebar
from graphs.trend_charts import summarize_trend, trend_figure
from services import data_service
from utils.session import current_user
from utils.ui import (
    accessibility_picker, ai_badge, ai_status_panel, chat_message_bubble, glass_card_close,
    glass_card_open, risk_badge, soft_divider,
)
from utils.wizard import wizard_nav, wizard_progress, wizard_reset, wizard_step


def render_pregnant_woman_dashboard() -> None:
    user = current_user()
    mother = data_service.get_mother(user["mother_id"])
    active = render_sidebar()

    render_alert_banner("pregnant_woman")

    if active == "Dashboard":
        _overview(mother)
    elif active == "Risk Check-Up":
        _risk_checkup(mother)
    elif active == "Pregnancy Timeline":
        _timeline(mother)
    elif active == "Nutrition":
        _nutrition(mother)
    elif active == "Child Tracking":
        _child_tracking(mother)
    elif active == "Trends":
        _trends(mother)
    elif active == "AI Companion":
        _companion(mother)
    else:
        _settings()


def _overview(mother: dict) -> None:
    week = data_service.pregnancy_week(mother)
    latest = data_service.latest_assessment(mother["id"])
    render_dashboard_header(f"Welcome, {mother['name']}", f"Week {week} of pregnancy · {mother['village']}")

    c1, c2, c3 = st.columns(3)
    with c1:
        glass_card_open()
        st.markdown(f"**Current Risk Level**")
        st.markdown(risk_badge(latest["risk_level"]) if latest else risk_badge("Low"), unsafe_allow_html=True)
        glass_card_close()
    with c2:
        glass_card_open()
        st.markdown("**Assessments Logged**")
        st.markdown(f"### {len(data_service.list_assessments(mother['id']))}")
        glass_card_close()
    with c3:
        glass_card_open()
        st.markdown("**Expected Delivery**")
        tl = schedule.pregnancy_timeline(mother, week) if mother.get("lmp") else None
        st.markdown(f"### {tl['edd'] if tl else '—'}")
        glass_card_close()

    soft_divider()
    if latest:
        st.markdown("#### Latest AI Risk Assessment")
        glass_card_open()
        st.markdown(risk_badge(latest["risk_level"]), unsafe_allow_html=True)
        st.write(f"**Score:** {latest['risk_score']}/100 &nbsp;·&nbsp; **Date:** {latest['date']}")
        st.markdown("**Why:**")
        for f in latest["risk_factors"]:
            st.markdown(f"- {f}")
        st.info(f"**Recommendation:** {latest['recommendation']}")
        glass_card_close()
    else:
        st.info("No assessments recorded yet. Your ASHA worker will record your first vitals, or you can do a self check-up under **Risk Check-Up**.")


_RISK_FIELD_DEFAULTS = {
    "risk_systolic": 118, "risk_diastolic": 76, "risk_weight": 58.0, "risk_height": 158.0,
    "risk_sugar": 95, "risk_hb": 11.5, "risk_symptoms": [],
}


def _risk_checkup(mother: dict) -> None:
    # Bugfix: these keys are only *created* when their step's widgets are
    # drawn. The Review step (and the "finish" handler) reads them
    # regardless of which step drew last, so without this guard a user who
    # somehow lands on Review before every widget key exists hits an
    # AttributeError/KeyError on st.session_state. setdefault() makes every
    # field safe to read from any step, every time.
    for _key, _default in _RISK_FIELD_DEFAULTS.items():
        st.session_state.setdefault(_key, _default)

    render_dashboard_header("AI Risk Check-Up", "A short, guided form — your answers are explained, not just scored.")
    steps = ["Vitals", "Blood Work", "Symptoms", "Review"]
    wizard_progress("risk", steps)
    step = wizard_step("risk")

    if step == 0:
        glass_card_open()
        st.number_input("Systolic BP (mmHg)", 60, 220, 118, key="risk_systolic")
        st.number_input("Diastolic BP (mmHg)", 40, 140, 76, key="risk_diastolic")
        st.number_input("Weight (kg)", 30.0, 150.0, 58.0, key="risk_weight")
        st.number_input("Height (cm)", 130.0, 190.0, 158.0, key="risk_height")
        glass_card_close()
    elif step == 1:
        glass_card_open()
        st.number_input("Blood Sugar (mg/dL)", 40, 400, 95, key="risk_sugar")
        st.number_input("Hemoglobin (g/dL)", 4.0, 18.0, 11.5, key="risk_hb", step=0.1)
        glass_card_close()
    elif step == 2:
        glass_card_open()
        st.multiselect(
            "Any symptoms today?",
            ["Mild nausea", "Mild fatigue", "Back pain", "Mild swelling in feet",
             "Severe headache", "Blurred vision", "Swelling in hands/face",
             "Reduced fetal movement", "Vaginal bleeding", "High fever", "Severe abdominal pain"],
            key="risk_symptoms",
        )
        glass_card_close()
    else:
        week = data_service.pregnancy_week(mother)
        glass_card_open()
        st.write("**Review your entries, then submit for the AI assessment.**")
        st.write(f"BP: {st.session_state.risk_systolic}/{st.session_state.risk_diastolic} mmHg")
        st.write(f"Weight/Height: {st.session_state.risk_weight} kg / {st.session_state.risk_height} cm")
        st.write(f"Sugar: {st.session_state.risk_sugar} mg/dL · Hemoglobin: {st.session_state.risk_hb} g/dL")
        st.write(f"Symptoms: {', '.join(st.session_state.get('risk_symptoms', [])) or 'None'}")
        glass_card_close()

    action = wizard_nav("risk", len(steps), on_finish_label="Submit for AI Assessment")
    if action == "finish":
        vitals = {
            "systolic": st.session_state.risk_systolic, "diastolic": st.session_state.risk_diastolic,
            "weight_kg": st.session_state.risk_weight, "height_cm": st.session_state.risk_height,
            "sugar_mg_dl": st.session_state.risk_sugar, "hemoglobin": st.session_state.risk_hb,
            "symptoms": [s.lower() for s in st.session_state.get("risk_symptoms", [])],
        }
        result = data_service.record_assessment(mother["id"], vitals, recorded_by="Self (Pregnant Woman)")
        wizard_reset("risk")
        st.success("Assessment saved — this is now visible to your ASHA worker and Doctor too.")

        # Rule engine already computed the score/level/factors inside
        # record_assessment(). Groq now turns those deterministic facts
        # into an explainable narrative; if AI is unavailable this
        # degrades to the same rule-based recommendation as before.
        from ai.risk_model import RiskAssessment
        rule_result = RiskAssessment(
            score=result["risk_score"], level=result["risk_level"],
            factors=result["risk_factors"], recommendation=result["recommendation"],
            referral_urgency=result.get("referral_urgency", "Routine"),
        )
        with st.spinner("AI is explaining your result…"):
            ai = groq_client.explain_maternal_risk(mother, vitals, rule_result)

        glass_card_open()
        col_a, col_b = st.columns([3, 1])
        with col_a:
            st.markdown(risk_badge(ai["risk_category"]), unsafe_allow_html=True)
        with col_b:
            st.markdown(ai_badge(ai["ai_generated"]), unsafe_allow_html=True)
        st.write(f"**Score:** {ai['risk_score']}/100")
        st.markdown("**Clinical explanation:**")
        st.write(ai["clinical_explanation"])
        st.markdown("**Why the AI classified this case this way:**")
        st.write(ai["why_classified"])
        st.markdown("**Immediate action:**")
        st.info(ai["immediate_action"])
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("**Hospital recommendation:**")
            st.write(ai["hospital_recommendation"])
            st.markdown("**Referral needed?**")
            st.write(ai["referral_need"])
            st.markdown("**Follow-up schedule:**")
            st.write(ai["follow_up_schedule"])
        with c2:
            st.markdown("**Warning signs to watch for:**")
            for w in ai["warning_signs"]:
                st.markdown(f"- {w}")
        st.markdown("**Lifestyle advice:**")
        for a in ai["lifestyle_advice"]:
            st.markdown(f"- {a}")
        st.markdown("**Nutrition guidance:**")
        st.write(ai["nutrition_guidance"])
        st.markdown("**Medication reminder:**")
        st.caption(ai["medication_reminder"])
        st.markdown("**Emergency instructions:**")
        st.error(ai["emergency_instructions"])
        glass_card_close()


def _timeline(mother: dict) -> None:
    render_dashboard_header("Pregnancy Timeline", "Built automatically from your last menstrual period.")
    if not mother.get("lmp"):
        st.warning("No LMP date on file yet — ask your ASHA worker to add it.")
        return
    week = data_service.pregnancy_week(mother)
    tl = schedule.pregnancy_timeline(mother, week)
    st.metric("Current Week", week, help="Calculated from your LMP date.")
    st.metric("Expected Delivery Date", tl["edd"])
    next_visit = schedule.next_anc_visit(week)
    if next_visit:
        st.info(f"Your next recommended ANC visit is around **week {next_visit}**.")

    with st.spinner("AI is building your stage summary…"):
        narrative = groq_client.pregnancy_stage_narrative(mother, week, tl)
    glass_card_open()
    st.markdown(ai_badge(narrative["ai_generated"]), unsafe_allow_html=True)
    st.markdown(f"**This stage:** {narrative['current_stage']}")
    st.markdown(f"**Baby's development:** {narrative['baby_development']}")
    st.markdown(f"**Your body:** {narrative['mothers_body_changes']}")
    st.markdown(f"**Exercise:** {narrative['exercise']}")
    st.markdown(f"**Preparing for delivery:** {narrative['preparation_for_delivery']}")
    glass_card_close()
    soft_divider()

    for item in tl["items"]:
        icon = "✅" if item["status"] == "done" else ("🟡" if item["status"] == "current" else "⚪")
        glass_card_open()
        st.markdown(f"{icon} **Week {item['week']} · {item['date']}** — {item['label']}")
        glass_card_close()


def _nutrition(mother: dict) -> None:
    render_dashboard_header("Personalized Nutrition Plan", "Grounded in your own latest vitals — with reasons, not guesses.")
    latest = data_service.latest_assessment(mother["id"])
    week = data_service.pregnancy_week(mother)
    plan = nutrition.nutrition_plan(mother, latest, week)

    with st.spinner("AI is personalizing your summary…"):
        narrative = groq_client.nutrition_narrative(mother, latest, week, plan)
    glass_card_open()
    st.markdown(ai_badge(narrative["ai_generated"]), unsafe_allow_html=True)
    st.write(narrative["summary"])
    glass_card_close()
    soft_divider()

    for item in plan:
        glass_card_open()
        st.markdown(f"**{item['title']}**")
        st.caption(item["why"])
        st.write(item["foods"])
        glass_card_close()


def _child_tracking(mother: dict) -> None:
    render_dashboard_header("Child Health Tracking", "Growth, nutrition, developmental milestones and immunization — in one place.")
    children = data_service.list_children(mother["id"])

    if not children:
        st.info("No child registered yet.")
        with st.expander("➕ Register a child"):
            name = st.text_input("Child's name", key="child_name")
            gender = st.selectbox("Gender", ["Male", "Female"], key="child_gender")
            dob = st.date_input("Date of birth", key="child_dob")
            birth_weight = st.number_input("Birth weight (kg)", 0.5, 6.0, 3.0, step=0.1, key="child_bw")
            if st.button("Register Child", key="child_register_btn"):
                data_service.register_child(mother["id"], {
                    "name": name, "gender": gender, "dob": str(dob), "birth_weight_kg": birth_weight,
                })
                st.success(f"{name} registered.")
                st.rerun()
        return

    child = children[0]
    age_months = data_service.child_age_months(child)
    st.markdown(f"### {child['name']} · {age_months:.1f} months old")

    tab_growth, tab_milestones, tab_immunization = st.tabs(["📈 Growth & Nutrition", "🧩 Milestones", "💉 Immunization"])

    with tab_growth:
        records = data_service.list_growth_records(child["id"])
        latest_w = records[-1]["weight_kg"] if records else child.get("birth_weight_kg")
        result = child_growth.assess_growth(age_months, latest_w)
        glass_card_open()
        st.markdown(f"**Status:** {result['status']}")
        st.write(result["note"])
        glass_card_close()

        if result.get("band"):
            with st.spinner("AI is analyzing growth…"):
                narrative = groq_client.child_growth_narrative(child, age_months, result)
            glass_card_open()
            st.markdown(ai_badge(narrative["ai_generated"]), unsafe_allow_html=True)
            st.markdown(f"**Growth analysis:** {narrative['growth_analysis']}")
            st.markdown(f"**Development milestones:** {narrative['development_milestones']}")
            st.markdown(f"**Vaccination:** {narrative['vaccination_explanation']}")
            glass_card_close()

        with st.expander("➕ Add a growth record"):
            w = st.number_input("Weight (kg)", 1.0, 30.0, float(latest_w or 3.0), step=0.1, key="growth_w")
            h = st.number_input("Height (cm)", 30.0, 130.0, 60.0, step=0.5, key="growth_h")
            notes = st.text_input("Notes (optional)", key="growth_notes")
            if st.button("Save Growth Record", key="growth_save_btn"):
                data_service.record_growth(child["id"], {
                    "age_months": age_months, "weight_kg": w, "height_cm": h, "notes": notes,
                })
                st.success("Saved.")
                st.rerun()

    with tab_milestones:
        for m in schedule.child_milestone_checklist(child):
            icon = "✅" if m["expected"] == "expected by now" else "⚪"
            st.markdown(f"{icon} **{m['age_months']} months** — {m['milestone']}")

    with tab_immunization:
        for v in schedule.child_immunization_plan(child):
            icon = {"done": "✅", "due soon": "🟡", "overdue": "🔴", "upcoming": "⚪"}.get(v["status"], "⚪")
            st.markdown(f"{icon} **{v['age_months']} mo · {v['due_date']}** — {v['vaccines']} _( {v['status']} )_")


def _trends(mother: dict) -> None:
    render_dashboard_header("Trend Analysis", "How your vitals and risk score are changing over time.")
    trend = data_service.trend_data(mother["id"])
    if not trend["dates"]:
        st.info("No assessments yet — complete a Risk Check-Up first.")
        return
    st.info(summarize_trend(trend))
    c1, c2 = st.columns(2)
    with c1:
        st.plotly_chart(trend_figure(trend, "systolic"), use_container_width=True)
        st.plotly_chart(trend_figure(trend, "hemoglobin", color="#34D399"), use_container_width=True)
    with c2:
        st.plotly_chart(trend_figure(trend, "sugar", color="#F59E0B"), use_container_width=True)
        st.plotly_chart(trend_figure(trend, "risk_score", color="#FB7185"), use_container_width=True)


def _companion(mother: dict) -> None:
    render_dashboard_header("AI Health Companion", "Ask about symptoms, diet, BP, sugar, vaccination and more.")
    history_key = f"chat_{mother['id']}"
    if history_key not in st.session_state:
        st.session_state[history_key] = [
            ("assistant", f"Hi {mother['name'].split()[0]}! I'm your CareNest AI companion. Ask me anything about your pregnancy.")
        ]

    for role, content in st.session_state[history_key]:
        chat_message_bubble(role, content)

    msg = st.chat_input("Type your question…")
    if msg:
        st.session_state[history_key].append(("user", msg))
        with st.spinner("AI Companion is thinking…"):
            reply = chatbot.answer(msg, mother_context=mother, history=st.session_state[history_key])
        st.session_state[history_key].append(("assistant", reply))
        st.rerun()


def _settings() -> None:
    render_dashboard_header("Settings", "Accessibility and display preferences.")
    ai_status_panel()
    soft_divider()
    accessibility_picker(key_prefix="pw")
