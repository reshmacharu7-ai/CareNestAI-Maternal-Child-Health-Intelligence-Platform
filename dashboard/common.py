"""
dashboard/common.py
--------------------
Shared chrome for every role dashboard: sidebar, header, and the
"Refresh" control that makes the JSON-backed cross-role sync visible
and trustworthy to the user.
"""

from __future__ import annotations

import streamlit as st

from services import data_service
from utils.session import ROLE_LABELS, current_user, log_out_user
from utils.ui import ecg_pulse_svg

NAV_ITEMS = {
    "pregnant_woman": [
        ("🏠", "Dashboard"), ("🧠", "Risk Check-Up"), ("🗓️", "Pregnancy Timeline"),
        ("🍎", "Nutrition"), ("👶", "Child Tracking"), ("📈", "Trends"),
        ("🤖", "AI Companion"), ("⚙️", "Settings"),
    ],
    "asha": [
        ("🏠", "Dashboard"), ("🧑‍🤝‍🧑", "My Mothers"), ("📝", "New Assessment"),
        ("🚨", "Priority List"), ("📤", "Referrals"), ("⚙️", "Settings"),
    ],
    "doctor": [
        ("🏠", "Dashboard"), ("📥", "Referred Mothers"), ("🗂️", "Case Review"),
        ("📄", "Referral PDFs"), ("⚙️", "Settings"),
    ],
    "phc": [
        ("🏠", "Dashboard"), ("📥", "Incoming Referrals"), ("📊", "Village Statistics"),
        ("⚙️", "Settings"),
    ],
}

ROLE_COLORS = {"pregnant_woman": "#FB7185", "asha": "#34D399", "doctor": "#22D3EE", "phc": "#8B5CF6"}


def role_pill(role: str) -> str:
    color = ROLE_COLORS.get(role, "#8FA1B8")
    return f'<span class="role-pill" style="color:{color};">{ROLE_LABELS.get(role, role).upper()}</span>'


def render_sidebar() -> str:
    user = current_user()
    role = user["role"]

    with st.sidebar:
        st.markdown(
            f"""
            <div style="padding:0.6rem 0 1rem 0;">
                <div style="font-family:var(--font-display); font-weight:700; font-size:1.25rem;">
                    CareNest <span class="gradient-text">AI</span>
                </div>
                <div style="margin-top:0.5rem;">{role_pill(role)}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.markdown(
            f'<div style="color:var(--text-muted); font-size:0.9rem;">Signed in as</div>'
            f'<div style="font-weight:600;">{user["full_name"]}</div>',
            unsafe_allow_html=True,
        )
        st.markdown('<hr class="divider-soft" />', unsafe_allow_html=True)

        selected = None
        for icon, label in NAV_ITEMS[role]:
            if st.button(f"{icon}  {label}", key=f"nav_{role}_{label}", use_container_width=True):
                selected = label
                st.session_state[f"{role}_active_nav"] = label

        active = st.session_state.get(f"{role}_active_nav", NAV_ITEMS[role][0][1])

        st.markdown('<hr class="divider-soft" />', unsafe_allow_html=True)
        if st.button("🔄  Refresh live data", key=f"refresh_{role}", use_container_width=True):
            st.rerun()
        if st.button("🚪  Logout", key=f"logout_{role}", use_container_width=True):
            log_out_user()
            st.rerun()

    return selected or active


def render_dashboard_header(title: str, subtitle: str) -> None:
    st.markdown(f'<h2>{title}</h2>', unsafe_allow_html=True)
    st.markdown(f'<div style="color:var(--text-muted);">{subtitle}</div>', unsafe_allow_html=True)
    st.markdown(ecg_pulse_svg(50), unsafe_allow_html=True)


def render_alert_banner(role: str) -> None:
    """Shows open alerts relevant to this role -- this is what makes an
    ASHA worker's High-risk entry visible to the Doctor/PHC instantly."""
    alerts = [a for a in data_service.list_alerts(unacknowledged_only=True) if role in a.get("target_roles", [])]
    if not alerts:
        return
    for a in alerts[:3]:
        mother = data_service.get_mother(a["mother_id"])
        name = mother["name"] if mother else a["mother_id"]
        st.markdown(
            f"""
            <div class="glass-card risk-critical" style="padding:0.9rem 1.2rem; margin-bottom:0.7rem;
                        border-color: rgba(248,113,113,0.6);">
                🚨 <b>{a['level']} risk alert — {name}</b><br>
                <span style="color:var(--text-muted); font-size:0.9rem;">{a['message']}</span>
            </div>
            """,
            unsafe_allow_html=True,
        )
