"""
app.py
------
CareNest AI -- main entry point.

Run with:
    streamlit run app.py

Routing only: initialises session state, loads the (unchanged) global
stylesheet, seeds the JSON data store on first run, and renders exactly
one screen based on the logged-in user's role. No database, no backend
server -- everything lives in data/store.py as JSON files.
"""

from __future__ import annotations

import streamlit as st

from data.store import seed_if_empty
from utils.session import current_role, init_session_state, is_authenticated
from utils.ui import apply_accessibility_mode, load_css

st.set_page_config(
    page_title="CareNest AI",
    page_icon="🤰",
    layout="wide",
    initial_sidebar_state="collapsed",
)


def bootstrap() -> None:
    init_session_state()
    load_css()
    apply_accessibility_mode()
    seed_if_empty()


def route() -> None:
    if is_authenticated():
        role = current_role()
        if role == "asha":
            from dashboard.asha_worker import render_asha_dashboard
            render_asha_dashboard()
        elif role == "doctor":
            from dashboard.doctor import render_doctor_dashboard
            render_doctor_dashboard()
        elif role == "phc":
            from dashboard.phc import render_phc_dashboard
            render_phc_dashboard()
        else:
            from dashboard.pregnant_woman import render_pregnant_woman_dashboard
            render_pregnant_woman_dashboard()
        return

    from views.landing import render_landing_page
    render_landing_page()


def main() -> None:
    bootstrap()
    route()


if __name__ == "__main__":
    main()
