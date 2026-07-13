"""
views/landing.py
-----------------
CareNest AI's single public screen: a compact hero + role-based login,
all on one page (no separate landing -> login navigation, and no long
scroll) exactly as requested. Every role's demo credentials are shown
right inside its own tab.
"""

from __future__ import annotations

import streamlit as st

from utils.session import DEMO_USERS, authenticate, log_in_user
from utils.ui import ecg_pulse_svg, soft_divider

ROLE_TABS = [
    ("pregnant_woman", "🤰 Pregnant Woman / Mother", "🤰"),
    ("asha", "🧑‍⚕️ ASHA Worker", "🧑‍⚕️"),
    ("doctor", "👨‍⚕️ Doctor", "👨‍⚕️"),
    ("phc", "🏥 Primary Health Centre", "🏥"),
]

FEATURES = [
    ("🧠", "Explainable Risk AI", "Predicts Low/Moderate/High/Critical risk with plain-language reasons, not a black box."),
    ("🍎", "Personalized Nutrition", "Meal guidance generated from the mother's own latest vitals."),
    ("🗓️", "Pregnancy Timeline", "Auto-built ANC visit, scan and delivery-window schedule from the LMP date."),
    ("💉", "Child Immunization Tracker", "Growth, nutrition, milestones and vaccine schedule for every child."),
    ("🚨", "Smart Alerts & Referrals", "A High/Critical result instantly raises an alert for ASHA, Doctor and PHC."),
    ("🤖", "AI Health Companion", "A chatbot mothers can ask about symptoms, diet, BP, sugar and more."),
]


def render_landing_page() -> None:
    _hero()
    soft_divider()
    _login_block()
    soft_divider()
    _features()
    _footer()


def _hero() -> None:
    left, right = st.columns([3, 2], gap="large")
    with left:
        st.markdown('<div class="hero-wrap">', unsafe_allow_html=True)
        st.markdown('<div class="hero-eyebrow">CARENEST AI &nbsp;·&nbsp; Maternal &amp; Child Health Platform</div>', unsafe_allow_html=True)
        st.markdown(
            '<div class="hero-title">Early Detection.<br><span class="gradient-text">Safer Mothers, Healthier Babies.</span></div>',
            unsafe_allow_html=True,
        )
        st.markdown(
            '<div class="hero-sub">CareNest AI connects Pregnant Women &amp; Mothers, ASHA Workers, Doctors and '
            "Primary Health Centres on one platform &mdash; AI-assisted risk detection, nutrition guidance, "
            "immunization tracking, and referrals that stay in sync across every role.</div>",
            unsafe_allow_html=True,
        )
        st.markdown(ecg_pulse_svg(60), unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)
    with right:
        st.markdown(
            """
            <div class="glass-card" style="margin-top:2.2rem;">
                <div style="font-family:var(--font-mono); color:var(--text-muted); font-size:0.8rem; letter-spacing:0.08em;">
                    VILLAGE SNAPSHOT · ERUMAIYUR
                </div>
                <div style="display:flex; justify-content:space-between; margin-top:0.9rem;">
                    <div>
                        <div style="color:var(--text-muted); font-size:0.8rem;">Mothers Tracked</div>
                        <div style="font-family:var(--font-mono); font-size:1.6rem; color:var(--accent-cyan);">4</div>
                    </div>
                    <div>
                        <div style="color:var(--text-muted); font-size:0.8rem;">High-Risk Flags</div>
                        <div style="font-family:var(--font-mono); font-size:1.6rem; color:var(--accent-rose);">1</div>
                    </div>
                    <div>
                        <div style="color:var(--text-muted); font-size:0.8rem;">AI Features</div>
                        <div style="font-family:var(--font-mono); font-size:1.6rem; color:var(--accent-violet);">8</div>
                    </div>
                </div>
                <div style="margin-top:1rem; color:var(--text-muted); font-size:0.85rem;">
                    Updates from an ASHA worker or Doctor appear for every other role the moment their screen refreshes.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )


def _login_block() -> None:
    st.markdown('<h2>Log in to <span class="gradient-text">CareNest AI</span></h2>', unsafe_allow_html=True)
    st.caption("This is a hackathon prototype — login uses fixed demo accounts shown in each tab below (no real database).")

    tabs = st.tabs([label for _, label, _ in ROLE_TABS])
    for (role, label, icon), tab in zip(ROLE_TABS, tabs):
        with tab:
            _login_form(role, icon)


def _login_form(role: str, icon: str) -> None:
    demo_accounts = [(email, acc) for email, acc in DEMO_USERS.items() if acc["role"] == role]

    col_form, col_demo = st.columns([3, 2], gap="large")

    with col_form:
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        email = st.text_input("Email", key=f"{role}_login_email", placeholder="you@demo.in")
        password = st.text_input("Password", key=f"{role}_login_password", type="password", placeholder="Enter password")
        if st.button(f"{icon} Log In", key=f"{role}_login_submit", use_container_width=True):
            ok, message, user = authenticate(email, password, expected_role=role)
            if ok:
                st.success(message)
                log_in_user(user)
                st.rerun()
            else:
                st.error(message)
        st.markdown("</div>", unsafe_allow_html=True)

    with col_demo:
        st.markdown(
            '<div class="glass-card" style="height:100%;">'
            '<div style="font-family:var(--font-mono); color:var(--accent-cyan); font-size:0.82rem; '
            'letter-spacing:0.06em; margin-bottom:0.5rem;">DEMO CREDENTIALS</div>',
            unsafe_allow_html=True,
        )
        for email, acc in demo_accounts:
            st.markdown(
                f"""
                <div style="margin-bottom:0.7rem; padding-bottom:0.6rem; border-bottom:1px dashed var(--panel-border);">
                    <div style="font-weight:600;">{acc['full_name']}</div>
                    <div style="font-family:var(--font-mono); font-size:0.85rem; color:var(--text-muted);">
                        {email} &nbsp;/&nbsp; {acc['password']}
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        st.markdown("</div>", unsafe_allow_html=True)


def _features() -> None:
    st.markdown("### The 8 AI features inside CareNest AI")
    cols = st.columns(3)
    for i, (icon, title, desc) in enumerate(FEATURES):
        with cols[i % 3]:
            st.markdown(
                f"""
                <div class="glass-card" style="min-height:150px; margin-bottom:1rem;">
                    <div class="feature-icon">{icon}</div>
                    <div style="font-family:var(--font-display); font-weight:600; margin-top:0.4rem;">{title}</div>
                    <div style="color:var(--text-muted); font-size:0.88rem; margin-top:0.3rem;">{desc}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )


def _footer() -> None:
    st.markdown(
        """
        <div style="text-align:center; color:var(--text-muted); font-size:0.85rem; padding: 1rem 0 2rem 0;">
            © 2026 CareNest AI &nbsp;·&nbsp; Early Detection · Smarter Decisions · Safer Mothers · Healthier Babies
        </div>
        """,
        unsafe_allow_html=True,
    )
