"""
utils/session.py
-----------------
Thin wrapper around st.session_state, plus demo-credential authentication.
There is no database and no bcrypt — this is a hackathon prototype, so
login is a fixed dictionary of demo accounts. This is exactly the kind
of thing that must NEVER be done this way in a real product, and the
login screen says so.
"""

from __future__ import annotations

from typing import Optional

import streamlit as st

_DEFAULTS = {
    "page": "landing",      # landing | dashboard
    "user": None,
    "a11y_mode": "Standard",
    "a11y_high_contrast": False,
}

# --------------------------------------------------------------------------
# DEMO CREDENTIALS -- shown directly on the login screen. Every "Pregnant
# Woman / Mother" account maps to one of the seeded mothers in data/store.py.
# --------------------------------------------------------------------------
DEMO_USERS = {
    "lakshmi@demo.in":  {"password": "demo123", "role": "pregnant_woman", "full_name": "Lakshmi Devi", "mother_id": "M001"},
    "fathima@demo.in":  {"password": "demo123", "role": "pregnant_woman", "full_name": "Fathima Beevi", "mother_id": "M002"},
    "priya@demo.in":    {"password": "demo123", "role": "pregnant_woman", "full_name": "Priya Ramesh", "mother_id": "M003"},
    "kavitha@demo.in":  {"password": "demo123", "role": "pregnant_woman", "full_name": "Kavitha Selvam", "mother_id": "M004"},
    "asha@demo.in":     {"password": "asha123", "role": "asha", "full_name": "Meena (ASHA Worker)", "asha_id": "ASHA01"},
    "doctor@demo.in":   {"password": "doc123",  "role": "doctor", "full_name": "Dr. Anand Kumar", "doctor_id": "DOC01"},
    "phc@demo.in":      {"password": "phc123",  "role": "phc", "full_name": "PHC Erumaiyur Staff"},
}

ROLE_LABELS = {
    "pregnant_woman": "Pregnant Woman / Mother",
    "asha": "ASHA Worker",
    "doctor": "Doctor",
    "phc": "Primary Health Centre",
}


def init_session_state() -> None:
    for key, default in _DEFAULTS.items():
        if key not in st.session_state:
            st.session_state[key] = default


def go_to(page: str) -> None:
    st.session_state["page"] = page


def authenticate(email: str, password: str, expected_role: str) -> tuple[bool, str, Optional[dict]]:
    email = (email or "").strip().lower()
    account = DEMO_USERS.get(email)
    if not account or account["role"] != expected_role:
        return False, "No matching demo account for this role. Use one of the demo credentials shown above.", None
    if account["password"] != password:
        return False, "Incorrect password.", None
    user = {"email": email, **account}
    return True, f"Welcome back, {account['full_name']}!", user


def log_in_user(user: dict) -> None:
    st.session_state["user"] = user
    st.session_state["page"] = "dashboard"


def log_out_user() -> None:
    st.session_state["user"] = None
    st.session_state["page"] = "landing"


def current_user() -> Optional[dict]:
    return st.session_state.get("user")


def is_authenticated() -> bool:
    return current_user() is not None


def current_role() -> Optional[str]:
    user = current_user()
    return user["role"] if user else None
