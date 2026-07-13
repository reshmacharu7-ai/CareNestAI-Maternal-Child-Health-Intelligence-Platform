"""
utils/ui.py
-----------
Small, reusable Streamlit UI helpers so pages stay readable. Every
function here just returns/writes markup -- no business logic.

Phase 3 additions: an accessibility-mode wrapper (Standard / Senior
Friendly / Kids Mode + optional high-contrast), animated number
counters for stat cards, and chat-bubble rendering for the AI
assistants.
"""

from __future__ import annotations

from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

CSS_PATH = Path(__file__).resolve().parent.parent / "assets" / "css" / "style.css"

_A11Y_CLASS_MAP = {
    "Standard": "",
    "Senior Friendly": "a11y-senior",
    "Kids Mode": "a11y-kids",
}


def load_css() -> None:
    """Injects the global glassmorphism stylesheet once per render."""
    css_text = CSS_PATH.read_text(encoding="utf-8")
    st.markdown(f"<style>{css_text}</style>", unsafe_allow_html=True)


def apply_accessibility_mode() -> None:
    """Reads the person's chosen accessibility mode from session state
    and injects a small script that toggles the matching CSS classes
    (defined in style.css) onto the app root. Safe no-op on 'Standard'.
    """
    mode = st.session_state.get("a11y_mode", "Standard")
    high_contrast = st.session_state.get("a11y_high_contrast", False)
    classes = [_A11Y_CLASS_MAP.get(mode, "")]
    if high_contrast:
        classes.append("a11y-contrast")
    classes = [c for c in classes if c]
    class_list = " ".join(classes)

    st.markdown(
        f"""
        <script>
        const root = window.parent.document.querySelector('.stApp');
        if (root) {{
            root.className = root.className
                .split(' ')
                .filter(c => !c.startsWith('a11y-'))
                .concat("{class_list}".split(' ').filter(Boolean))
                .join(' ');
        }}
        </script>
        """,
        unsafe_allow_html=True,
    )


def accessibility_picker(key_prefix: str = "a11y") -> None:
    """Renders the Standard / Senior Friendly / Kids Mode + high-contrast
    picker. Call this from each dashboard's Settings tab."""
    st.markdown("##### ♿ Accessibility & Display")
    st.caption(
        "Choose a viewing mode that works best for you. Senior Friendly uses larger "
        "text and turns off motion; Kids Mode is playful and simplified."
    )
    mode = st.radio(
        "Display mode",
        ["Standard", "Senior Friendly", "Kids Mode"],
        index=["Standard", "Senior Friendly", "Kids Mode"].index(
            st.session_state.get("a11y_mode", "Standard")
        ),
        key=f"{key_prefix}_mode_radio",
        horizontal=True,
    )
    high_contrast = st.checkbox(
        "Extra high-contrast (black background, white/yellow text)",
        value=st.session_state.get("a11y_high_contrast", False),
        key=f"{key_prefix}_contrast_checkbox",
    )
    if mode != st.session_state.get("a11y_mode") or high_contrast != st.session_state.get("a11y_high_contrast"):
        st.session_state["a11y_mode"] = mode
        st.session_state["a11y_high_contrast"] = high_contrast
        st.rerun()


def ecg_pulse_svg(height: int = 90) -> str:
    """Returns the markup for the animated ECG signature line used on
    the hero section and dashboard headers."""
    return f"""
    <div class="ecg-wrap" style="height:{height}px;">
      <svg viewBox="0 0 1200 90" preserveAspectRatio="none" width="100%" height="100%">
        <polyline class="ecg-line" points="
          0,45 90,45 110,45 125,15 140,75 155,10 170,80 185,45 220,45
          320,45 340,45 355,15 370,75 385,10 400,80 415,45 450,45
          550,45 570,45 585,15 600,75 615,10 630,80 645,45 680,45
          780,45 800,45 815,15 830,75 845,10 860,80 875,45 910,45
          1010,45 1030,45 1045,15 1060,75 1075,10 1090,80 1105,45 1200,45
        "/>
      </svg>
    </div>
    """


def glass_card_open(extra_style: str = "") -> None:
    st.markdown(f'<div class="glass-card" style="{extra_style}">', unsafe_allow_html=True)


def glass_card_close() -> None:
    st.markdown("</div>", unsafe_allow_html=True)


def stat_card(value: str, label: str) -> str:
    return f"""
    <div class="glass-card stat-card">
      <div class="stat-value">{value}</div>
      <div class="stat-label">{label}</div>
    </div>
    """


def animated_stat_card(value: float, label: str, suffix: str = "", decimals: int = 0, height: int = 130) -> None:
    """Renders a glass stat-card whose number counts up from 0 on every
    render -- a small, cheap way to make the dashboards feel alive."""
    components.html(
        f"""
        <div style="font-family:'Space Grotesk',sans-serif; background:rgba(255,255,255,0.07);
                    border:1px solid rgba(255,255,255,0.16); border-radius:20px; padding:1.1rem 1rem;
                    text-align:center; backdrop-filter:blur(18px);">
          <div id="val" style="font-family:'JetBrains Mono',monospace; font-size:2.1rem; font-weight:700;
                      color:#22D3EE; text-shadow:0 0 18px rgba(34,211,238,0.35);">0{suffix}</div>
          <div style="color:#AEC0D8; font-size:0.92rem; margin-top:0.3rem; font-weight:500;">{label}</div>
        </div>
        <script>
          const target = {value};
          const el = document.getElementById('val');
          const decimals = {decimals};
          let start = null;
          const duration = 900;
          function step(ts) {{
            if (!start) start = ts;
            const progress = Math.min((ts - start) / duration, 1);
            const current = target * progress;
            el.textContent = current.toFixed(decimals) + "{suffix}";
            if (progress < 1) requestAnimationFrame(step);
            else el.textContent = target.toFixed(decimals) + "{suffix}";
          }}
          requestAnimationFrame(step);
        </script>
        """,
        height=height,
    )


def role_pill(role: str) -> str:
    colors = {"admin": "#8B5CF6", "doctor": "#22D3EE", "patient": "#34D399"}
    color = colors.get(role, "#8FA1B8")
    return (
        f'<span class="role-pill" style="color:{color};">'
        f'{role.upper()}</span>'
    )


def risk_badge(level: str) -> str:
    css_class = {
        "Low": "risk-low",
        "Moderate": "risk-moderate",
        "High": "risk-high",
        "Critical": "risk-critical",
    }.get(level, "risk-low")
    icon = {"Low": "✅", "Moderate": "🟡", "High": "🟠", "Critical": "🔴"}.get(level, "✅")
    return f'<span class="risk-badge {css_class}">{icon} {level} Risk</span>'


def chat_message_bubble(role: str, content: str) -> None:
    """Renders one chat message bubble (role is 'user' or 'assistant')."""
    css_role = "user" if role == "user" else "assistant"
    label = "You" if role == "user" else "🤖 AI Assistant"
    align = "text-align:right;" if css_role == "user" else "text-align:left;"
    st.markdown(
        f"""
        <div style="display:flex; flex-direction:column; {align}">
            <div class="chat-role-label">{label}</div>
            <div class="chat-bubble {css_role}">{content}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def typing_indicator() -> None:
    st.markdown(
        '<div class="chat-bubble assistant typing-dots">'
        "<span></span><span></span><span></span></div>",
        unsafe_allow_html=True,
    )


def soft_divider() -> None:
    st.markdown('<hr class="divider-soft" />', unsafe_allow_html=True)


def ai_status_panel() -> None:
    """Small, honest 'is Groq actually connected?' panel. Call this from
    every role's Settings tab so a missing/expired key or a deprecated
    model name (which fails silently by design elsewhere, to protect the
    demo) is easy to diagnose instead of just looking like a dumber chatbot."""
    from ai import groq_client
    s = groq_client.status()
    st.markdown("##### 🤖 AI Connection Status")
    if s["client_ready"]:
        st.success(f"Connected to Groq · model: `{s['model']}`")
    else:
        st.warning(
            f"AI is running in rule-based fallback mode ({s['detail']}). "
            "All features still work, using the deterministic rule engine instead of Groq."
        )
    if s.get("last_call_error"):
        st.caption(f"Most recent Groq call failed and fell back automatically: {s['last_call_error']}")


def ai_badge(ai_generated: bool) -> str:
    """Small honest badge: shows whether this text came from Groq or the
    deterministic rule-based fallback. Never misrepresents which it is."""
    if ai_generated:
        return ('<span class="risk-badge" style="background:rgba(139,92,246,0.18); '
                'color:#C4B5FD; border:1px solid rgba(139,92,246,0.4);">✨ AI-Generated (Groq)</span>')
    return ('<span class="risk-badge" style="background:rgba(148,163,184,0.15); '
            'color:#94A3B8; border:1px solid rgba(148,163,184,0.35);">⚙️ Rule-Based (offline)</span>')
