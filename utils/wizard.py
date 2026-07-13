"""
utils/wizard.py
----------------
A tiny, reusable multi-step wizard so registration / assessment forms
are broken into "Next / Back" steps instead of one long scrolling form.
"""

from __future__ import annotations

import streamlit as st


def wizard_step(key: str) -> int:
    """Returns the current step (0-indexed) for a wizard identified by key."""
    state_key = f"wizard_{key}_step"
    if state_key not in st.session_state:
        st.session_state[state_key] = 0
    return st.session_state[state_key]


def wizard_progress(key: str, step_labels: list[str]) -> None:
    step = wizard_step(key)
    total = len(step_labels)
    pct = int(((step + 1) / total) * 100)
    st.markdown(
        f"""
        <div style="margin-bottom:1rem;">
          <div style="display:flex; justify-content:space-between; font-family:var(--font-mono);
                      font-size:0.8rem; color:var(--text-muted); margin-bottom:0.4rem;">
            <span>Step {step + 1} of {total}: {step_labels[step]}</span>
            <span>{pct}%</span>
          </div>
          <div style="background:rgba(255,255,255,0.08); border-radius:999px; height:8px; overflow:hidden;">
            <div style="width:{pct}%; height:100%; background:linear-gradient(90deg, var(--accent-cyan), var(--accent-violet));
                        transition:width 0.3s ease;"></div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def wizard_nav(key: str, total_steps: int, on_finish_label: str = "Submit", can_advance: bool = True) -> str:
    """Renders Back / Next (or Submit on the last step) buttons.
    Returns 'next', 'back', 'finish' or '' depending on what was clicked."""
    step = wizard_step(key)
    state_key = f"wizard_{key}_step"
    is_last = step == total_steps - 1

    col_back, col_spacer, col_next = st.columns([1, 2, 1])
    action = ""
    with col_back:
        if step > 0:
            if st.button("← Back", key=f"{key}_back_{step}", use_container_width=True):
                st.session_state[state_key] = step - 1
                action = "back"
    with col_next:
        label = on_finish_label if is_last else "Next →"
        if st.button(label, key=f"{key}_next_{step}", use_container_width=True, disabled=not can_advance):
            if is_last:
                action = "finish"
            else:
                st.session_state[state_key] = step + 1
                action = "next"
    if action in ("next", "back"):
        st.rerun()
    return action


def wizard_reset(key: str) -> None:
    st.session_state[f"wizard_{key}_step"] = 0
