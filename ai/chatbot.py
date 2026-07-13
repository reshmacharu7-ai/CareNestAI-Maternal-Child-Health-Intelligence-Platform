"""
ai/chatbot.py
-------------
AI Feature 9: AI Health Companion.

Two layers:
  1. A crisis-safety guard (`_CRISIS_RE`) that is checked FIRST, always,
     regardless of whether Groq is configured. Self-harm language is
     never sent through the AI or keyword "helpful answer" path.
  2. `answer()` — the public entry point used by the dashboards. It tries
     Groq for a real conversational reply (see ai/groq_client.py) and
     transparently falls back to the keyword-grounded Q&A below if no
     API key is configured or the call fails for any reason. This means
     the companion always works, with or without an API key.
"""

from __future__ import annotations

import re

_CRISIS_RE = re.compile(
    r"\bsuicid\w*\b|\bkill myself\b|\bend my life\b|\bwant to die\b|\bself[\s-]?harm\w*\b|\bhurt(ing)? myself\b",
    re.IGNORECASE,
)

CRISIS_RESPONSE = (
    "I'm really glad you told me this, and I want you to be safe. I can't help with this myself, "
    "but please reach out right now:\n\n"
    "- **iCall (India)** — 9152987821 (Mon–Sat, 8am–10pm)\n"
    "- **Vandrevala Foundation Helpline (India)** — 1860-2662-345 / 1800-2333-330 (24/7)\n"
    "- If you're outside India, please contact your local emergency number.\n\n"
    "If you're in immediate danger, call your local emergency number now, and please also tell "
    "your ASHA worker, a family member, or your doctor what you're going through."
)

_QA = [
    (r"papaya", "Ripe papaya in normal food amounts is generally considered safe. **Unripe/semi-ripe papaya** is best avoided — it can trigger contractions. When in doubt, ask your ASHA worker or doctor."),
    (r"swell|swelling", "Mild swelling in the feet/ankles by evening is common in pregnancy. But **sudden swelling in the hands or face, especially with headache or blurred vision, can be a warning sign of pre-eclampsia** — please contact your ASHA worker or doctor the same day if that happens."),
    (r"anemia|anaemia|hemoglobin|haemoglobin", "Anemia means your blood has fewer healthy red cells than it should, often from low iron. In pregnancy it's checked with a hemoglobin (Hb) test — 11 g/dL or above is the healthy target. Iron-folic acid tablets, iron-rich foods (leafy greens, jaggery, eggs) and a vitamin-C food with meals all help your body absorb iron better."),
    (r"blood pressure|bp\b|hypertension", "Blood pressure is the force of blood against your artery walls. In pregnancy, readings consistently at or above 140/90 mmHg need medical review, since high BP can lead to pre-eclampsia. Reducing salty/oily food and attending every check-up helps your ASHA worker and doctor catch this early."),
    (r"sugar|diabet|glucose", "Gestational diabetes is high blood sugar that can develop during pregnancy. It's checked with a glucose test, usually around week 24-28. Eating smaller, balanced meals with whole grains and vegetables, and staying active, both help keep sugar levels in a healthy range."),
    (r"headache", "Occasional mild headaches can happen in pregnancy, but a **sudden, severe headache — especially with blurred vision or swelling — needs same-day medical attention**, as it can be a warning sign."),
    (r"movement|kick", "From around week 18-20 you should start feeling regular baby movements, becoming a fairly consistent daily pattern by the third trimester. **A noticeable reduction in movement should be reported to your ASHA worker or doctor promptly.**"),
    (r"vaccin|immuniz|immunis", "For the mother, the Tetanus Toxoid (TT) vaccine is given during pregnancy. For the baby after birth, there's a fixed national schedule (BCG, OPV, Pentavalent, Measles-Rubella and more) — you can see your child's personalised schedule under the Immunization tab."),
    (r"diet|food|eat|nutrition", "A good pregnancy diet includes one extra balanced meal a day, iron-rich foods, calcium (milk/curd/ragi), and plenty of water. You can see a plan built from your own latest vitals under the Nutrition tab."),
    (r"exercise|walk", "Gentle activity like a daily walk is usually safe and encouraged unless your doctor has advised rest for a specific risk. Avoid heavy lifting or strenuous exercise."),
    (r"delivery|labor|labour|due date|edd", "Your Expected Delivery Date (EDD) is calculated from your last menstrual period, roughly 40 weeks later. You can see your personalised timeline under the Pregnancy Timeline tab."),
]

_FALLBACK = (
    "I don't have a specific answer for that yet, but I'd encourage you to ask your ASHA worker or "
    "doctor directly — they can see your full record. You can also try asking about symptoms, "
    "nutrition, blood pressure, sugar, anemia, vaccination, or your due date."
)


def _rule_based_answer(message: str, mother_context: dict | None = None) -> str:
    """The original offline, keyword-grounded Q&A. Used as the fallback
    path when Groq isn't configured/available, and importable directly
    by ai/groq_client.py to avoid a circular import at module load time."""
    text = message.lower()
    for pattern, reply in _QA:
        if re.search(pattern, text):
            return reply
    return _FALLBACK


def answer(message: str, mother_context: dict | None = None,
           history: list[tuple[str, str]] | None = None) -> str:
    """Public entry point used by every dashboard. Crisis detection is
    checked here, first, before anything else -- including before Groq
    is ever called -- so it can never be bypassed by the AI path."""
    if _CRISIS_RE.search(message):
        return CRISIS_RESPONSE

    from ai.groq_client import chatbot_reply
    reply, _ai_generated = chatbot_reply(message, mother_context=mother_context, history=history)
    return reply
