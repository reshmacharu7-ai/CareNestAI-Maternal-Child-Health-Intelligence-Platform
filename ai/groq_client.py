"""
ai/groq_client.py
------------------
The one place in CareNest AI that talks to Groq.

Pipeline used everywhere in this app:

    Rule Engine (ai/risk_model.py, ai/nutrition.py, ai/schedule.py, ...)
            |
            v
    deterministic, traceable clinical facts (numbers, thresholds, flags)
            |
            v
    Groq LLM  (this file)
            |
            v
    explainable natural-language reasoning / recommendations
            |
            v
    structured dict returned to the dashboard -- ALWAYS, even on failure

Hard rules this module follows:
  * The LLM is only ever handed facts that were already computed by a
    rule engine. It is asked to explain/translate them, never to invent
    a risk score, a diagnosis, or a number that wasn't given to it.
  * If GROQ_API_KEY is missing, the `groq` package isn't installed, the
    network call fails, times out, or the model returns malformed JSON,
    every public function here falls back to a deterministic, rule-based
    result instead of raising. The app must never crash or show a blank
    screen because of AI.
  * The API key is read from the environment / .env and is never logged,
    echoed back to the UI, or included in any returned dict.
  * Every returned dict includes "ai_generated": True/False so the UI can
    show a small "✨ AI" vs "Rule-based" badge honestly.
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any

# --------------------------------------------------------------------------
# Environment / .env loading (optional dependency -- degrade quietly)
# --------------------------------------------------------------------------
try:
    from dotenv import load_dotenv

    load_dotenv(Path(__file__).resolve().parent.parent / ".env")
except Exception:
    pass

try:
    from groq import Groq  # type: ignore
except Exception:  # package not installed -- fine, we fall back everywhere
    Groq = None  # type: ignore

GROQ_API_KEY = (os.getenv("GROQ_API_KEY") or "").strip()
# NOTE: llama-3.3-70b-versatile was deprecated by Groq on 2026-06-17.
# openai/gpt-oss-120b is Groq's recommended replacement (see
# https://console.groq.com/docs/deprecations). Override via .env if you
# want a different model -- no code change needed.
GROQ_MODEL = (os.getenv("GROQ_MODEL") or "openai/gpt-oss-120b").strip()
GROQ_TEMPERATURE = float(os.getenv("GROQ_TEMPERATURE", "0.4"))
GROQ_MAX_TOKENS = int(os.getenv("GROQ_MAX_TOKENS", "900"))
_MAX_RETRIES = 2
_RETRY_BACKOFF_SECONDS = 0.6

_client: Any = None
_init_error: str | None = None
_last_call_error: str | None = None  # most recent runtime failure, for diagnostics only
if GROQ_API_KEY and Groq is not None:
    try:
        _client = Groq(api_key=GROQ_API_KEY)
    except Exception as exc:  # pragma: no cover - defensive
        _client = None
        _init_error = str(exc)
elif not GROQ_API_KEY:
    _init_error = "GROQ_API_KEY not set"
elif Groq is None:
    _init_error = "groq package not installed"


def is_available() -> bool:
    """True only if we have a usable, initialised Groq client."""
    return _client is not None


def status() -> dict:
    """Small, safe (no secrets) status dict — handy for a Settings page."""
    return {
        "configured": bool(GROQ_API_KEY),
        "client_ready": is_available(),
        "model": GROQ_MODEL,
        "detail": None if is_available() else _init_error,
        "last_call_error": _last_call_error,
    }


SYSTEM_PROMPT_BASE = (
    "You are CareNest AI, a clinical decision-SUPPORT assistant embedded in a maternal and "
    "child health platform used in rural India by ASHA workers, doctors, Primary Health Centre "
    "(PHC) staff, and pregnant women themselves. You are always given a set of facts that were "
    "already computed by a deterministic, rule-based clinical engine (vitals, thresholds, a risk "
    "score and risk factors). Your job is ONLY to explain, contextualise, and translate those "
    "facts into clear, warm, actionable language — never to invent a diagnosis, a number, or a "
    "clinical fact that was not given to you. If something is not in the provided facts, say it "
    "is not available instead of guessing. Never contradict the computed risk level or score. "
    "Always tell the user to seek in-person medical care for anything High or Critical. Keep "
    "language accessible to a non-medical reader unless a clinical/doctor-facing tone is asked for."
)


# --------------------------------------------------------------------------
# Low-level call helpers
# --------------------------------------------------------------------------
def _chat(messages: list[dict], *, temperature: float | None = None,
          max_tokens: int | None = None, json_mode: bool = False) -> str | None:
    """Calls Groq with retries. Returns the raw text, or None on any failure.
    Never raises -- callers always get a usable fallback -- but the failure
    reason is recorded in _last_call_error so it's visible via status()
    instead of vanishing silently."""
    global _last_call_error
    if not is_available():
        return None
    for attempt in range(_MAX_RETRIES + 1):
        try:
            kwargs: dict[str, Any] = dict(
                model=GROQ_MODEL,
                messages=messages,
                temperature=GROQ_TEMPERATURE if temperature is None else temperature,
                max_tokens=GROQ_MAX_TOKENS if max_tokens is None else max_tokens,
            )
            if json_mode:
                kwargs["response_format"] = {"type": "json_object"}
            resp = _client.chat.completions.create(**kwargs)
            _last_call_error = None
            return resp.choices[0].message.content
        except Exception as exc:
            _last_call_error = f"{type(exc).__name__}: {exc}"
            if attempt < _MAX_RETRIES:
                time.sleep(_RETRY_BACKOFF_SECONDS * (attempt + 1))
                continue
            return None
    return None


def _parse_json(raw: str | None) -> dict | None:
    if raw is None:
        return None
    text = raw.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.lower().startswith("json"):
            text = text[4:]
    try:
        return json.loads(text)
    except Exception:
        start, end = text.find("{"), text.rfind("}")
        if start != -1 and end != -1 and end > start:
            try:
                return json.loads(text[start:end + 1])
            except Exception:
                return None
        return None


def generate_json(prompt: str, system: str | None = None, **kwargs) -> dict | None:
    messages = [
        {"role": "system", "content": (system or SYSTEM_PROMPT_BASE) +
         " Respond with a single valid JSON object only. No markdown, no code fences, no preamble."},
        {"role": "user", "content": prompt},
    ]
    return _parse_json(_chat(messages, json_mode=True, **kwargs))


def generate_text(prompt: str, system: str | None = None, **kwargs) -> str | None:
    messages = [{"role": "system", "content": system or SYSTEM_PROMPT_BASE},
                {"role": "user", "content": prompt}]
    return _chat(messages, **kwargs)


def _facts_block(facts: dict) -> str:
    return json.dumps(facts, default=str, indent=2)


# ==========================================================================
# 1. MATERNAL RISK EXPLANATION  (Pregnant Woman + ASHA "New Assessment")
# ==========================================================================
def explain_maternal_risk(mother: dict, vitals: dict, rule_result) -> dict:
    """rule_result is a RiskAssessment from ai/risk_model.py (already computed).
    Returns a dict the UI can render directly; always populated, AI or not."""
    fallback = {
        "risk_category": rule_result.level,
        "risk_score": rule_result.score,
        "confidence": "Rule-based (deterministic)",
        "clinical_explanation": "This category was reached by the rule-based screening engine from: "
                                 + "; ".join(rule_result.factors),
        "why_classified": "; ".join(rule_result.factors),
        "immediate_action": rule_result.recommendation,
        "hospital_recommendation": "Primary Health Centre, Erumaiyur" if rule_result.level in ("High", "Critical")
                                    else "Continue routine ANC visits at your usual facility.",
        "referral_need": "Yes" if rule_result.level in ("High", "Critical") else "No",
        "warning_signs": ["Severe headache", "Blurred vision", "Swelling in hands/face",
                           "Reduced fetal movement", "Vaginal bleeding", "High fever"],
        "lifestyle_advice": ["Rest adequately and avoid strenuous activity",
                              "Stay well hydrated", "Attend every scheduled ANC visit"],
        "medication_reminder": "Continue any iron-folic acid / medication prescribed by your doctor — "
                                "do not start or stop medication without medical advice.",
        "nutrition_guidance": "See the Nutrition tab for a plan built from your latest vitals.",
        "follow_up_schedule": rule_result.referral_urgency,
        "emergency_instructions": "If any warning sign above appears, contact your ASHA worker, doctor, "
                                   "or go to the nearest hospital immediately — do not wait.",
        "ai_generated": False,
    }
    if not is_available():
        return fallback

    facts = {
        "mother_age": mother.get("age"),
        "gravida": mother.get("gravida"),
        "previous_miscarriage": mother.get("previous_miscarriage", False),
        "pregnancy_week": vitals.get("week"),
        "vitals": {k: v for k, v in vitals.items() if k != "symptoms"},
        "reported_symptoms": vitals.get("symptoms", []),
        "computed_risk_score": rule_result.score,
        "computed_risk_level": rule_result.level,
        "computed_risk_factors": rule_result.factors,
        "rule_based_recommendation": rule_result.recommendation,
        "referral_urgency": rule_result.referral_urgency,
    }
    prompt = (
        "Deterministic clinical facts computed by our rule engine for a pregnant woman:\n"
        f"{_facts_block(facts)}\n\n"
        "Using ONLY these facts (do not invent new medical facts or change the risk level/score), "
        "return a JSON object with exactly these keys:\n"
        "clinical_explanation (2-4 sentences explaining the risk category in plain language), "
        "why_classified (1-3 sentences on which specific factors drove this classification), "
        "immediate_action (1-2 sentences, what to do right now), "
        "hospital_recommendation (1 sentence), "
        "referral_need ('Yes', 'No', or 'Consider'), "
        "warning_signs (list of 3-6 short strings to watch for), "
        "lifestyle_advice (list of 3-5 short, general, non-prescriptive strings), "
        "medication_reminder (1 sentence, general and non-prescriptive — never name a specific drug or dose), "
        "nutrition_guidance (1-3 sentences, general), "
        "follow_up_schedule (1 sentence on when to next check in), "
        "emergency_instructions (1-2 sentences on what to do immediately if a warning sign appears)."
    )
    data = generate_json(prompt)
    if not data:
        return fallback
    merged = {**fallback, **{k: v for k, v in data.items() if v}}
    merged["risk_category"] = rule_result.level  # never let the LLM override computed facts
    merged["risk_score"] = rule_result.score
    merged["ai_generated"] = True
    return merged


# ==========================================================================
# 2. AI HEALTH COMPANION CHATBOT
# ==========================================================================
def chatbot_reply(message: str, mother_context: dict | None = None,
                   history: list[tuple[str, str]] | None = None) -> tuple[str, bool]:
    """Returns (reply_text, ai_generated). Caller is responsible for the
    crisis-language safety check BEFORE calling this (see ai/chatbot.py) —
    this function is never used for that path."""
    from ai.chatbot import _rule_based_answer as rule_based_answer

    if not is_available():
        return rule_based_answer(message, mother_context), False

    context_lines = []
    if mother_context:
        context_lines.append(
            f"The mother's name is {mother_context.get('name', 'the user')}, "
            f"village {mother_context.get('village', '—')}."
        )
    convo = ""
    if history:
        recent = history[-6:]
        convo = "\n".join(f"{'User' if r == 'user' else 'Assistant'}: {c}" for r, c in recent)

    system = SYSTEM_PROMPT_BASE + (
        " You are chatting directly with a pregnant woman or new mother in a chat widget. "
        "Answer in simple, warm, everyday language (a few short sentences or a short list). "
        "Cover pregnancy, nutrition, baby care, vaccination, mental health, emergency symptoms, "
        "medical reports, and referral questions. For anything that sounds like a medical emergency "
        "(heavy bleeding, severe headache with vision changes, reduced fetal movement, severe pain, "
        "high fever, difficulty breathing), clearly say to contact their ASHA worker/doctor or go to "
        "the hospital immediately. You are not a replacement for a doctor — say so when relevant, "
        "briefly, without being repetitive about it every message."
    )
    prompt = (
        (f"{' '.join(context_lines)}\n" if context_lines else "")
        + (f"Recent conversation so far:\n{convo}\n\n" if convo else "")
        + f"New message from the user: {message}"
    )
    reply = generate_text(prompt, system=system, max_tokens=400)
    if not reply:
        return rule_based_answer(message, mother_context), False
    return reply.strip(), True


# ==========================================================================
# 3. PREGNANCY TIMELINE NARRATIVE
# ==========================================================================
def pregnancy_stage_narrative(mother: dict, week: int, timeline: dict) -> dict:
    fallback = {
        "current_stage": f"Week {week} of pregnancy.",
        "baby_development": "See the milestone list below for scans and developmental checkpoints.",
        "mothers_body_changes": "Changes vary by trimester — expect increasing appetite, energy shifts, "
                                 "and visible bump growth as the pregnancy progresses.",
        "exercise": "Gentle daily walking is generally safe unless your doctor has advised rest.",
        "preparation_for_delivery": "Discuss a birth plan and nearest facility with your ASHA worker "
                                     "as you approach week 36.",
        "ai_generated": False,
    }
    if not is_available():
        return fallback
    facts = {"pregnancy_week": week, "edd": timeline.get("edd"),
             "upcoming_milestones": [i for i in timeline.get("items", []) if i["status"] != "done"][:4]}
    prompt = (
        f"Deterministic pregnancy schedule facts:\n{_facts_block(facts)}\n\n"
        "Return a JSON object with keys: current_stage (1-2 sentences), "
        "baby_development (2-3 sentences, general/typical development for this week — no invented "
        "measurements), mothers_body_changes (2-3 sentences), exercise (1-2 sentences), "
        "preparation_for_delivery (1-2 sentences, only relevant detail for this week's stage)."
    )
    data = generate_json(prompt)
    if not data:
        return fallback
    merged = {**fallback, **{k: v for k, v in data.items() if v}}
    merged["ai_generated"] = True
    return merged


# ==========================================================================
# 4. CHILD GROWTH NARRATIVE
# ==========================================================================
def child_growth_narrative(child: dict, age_months: float, growth_result: dict) -> dict:
    fallback = {
        "growth_analysis": growth_result.get("note", "No note available."),
        "development_milestones": "See the Milestones tab for the age-appropriate checklist.",
        "vaccination_explanation": "See the Immunization tab for the national schedule and current status.",
        "ai_generated": False,
    }
    if not is_available():
        return fallback
    facts = {"child_age_months": age_months, "growth_status": growth_result.get("status"),
             "growth_note": growth_result.get("note"), "healthy_band_kg": growth_result.get("band")}
    prompt = (
        f"Deterministic child-growth facts:\n{_facts_block(facts)}\n\n"
        "Return a JSON object with keys: growth_analysis (2-3 sentences explaining the status simply "
        "to a parent), development_milestones (1-2 sentences on what's typical around this age), "
        "vaccination_explanation (1-2 sentences on why vaccination on schedule matters at this age)."
    )
    data = generate_json(prompt)
    if not data:
        return fallback
    merged = {**fallback, **{k: v for k, v in data.items() if v}}
    merged["ai_generated"] = True
    return merged


# ==========================================================================
# 5. NUTRITION NARRATIVE (on top of the deterministic plan)
# ==========================================================================
def nutrition_narrative(mother: dict, latest_assessment: dict | None, week: int, plan: list[dict]) -> dict:
    fallback = {
        "summary": "This plan is built from your latest recorded vitals and pregnancy stage — "
                    "see each card below for the specific reason it was included.",
        "ai_generated": False,
    }
    if not is_available():
        return fallback
    facts = {"pregnancy_week": week,
             "latest_vitals": {k: (latest_assessment or {}).get(k) for k in
                                ("hemoglobin", "sugar_mg_dl", "systolic")},
             "plan_titles": [p["title"] for p in plan]}
    prompt = (
        f"Deterministic nutrition-plan facts:\n{_facts_block(facts)}\n\n"
        "Return a JSON object with one key: summary — 2-3 warm, encouraging sentences tying the plan "
        "items together for the mother, referencing her stage and any flagged vitals in plain language."
    )
    data = generate_json(prompt)
    if not data or not data.get("summary"):
        return fallback
    return {"summary": data["summary"], "ai_generated": True}


# ==========================================================================
# 6. ASHA VISIT SUMMARY / NOTES
# ==========================================================================
def asha_visit_summary(mother: dict, vitals: dict, rule_result) -> dict:
    fallback = {
        "visit_summary": f"Vitals recorded for {mother.get('name', 'the mother')}: risk level "
                          f"{rule_result.level} (score {rule_result.score}/100). "
                          + "; ".join(rule_result.factors),
        "urgency": rule_result.level,
        "missing_data": [k for k in ("systolic", "diastolic", "sugar_mg_dl", "hemoglobin",
                                      "weight_kg", "height_cm") if not vitals.get(k)],
        "follow_up_interval": rule_result.referral_urgency,
        "ai_visit_notes": rule_result.recommendation,
        "ai_generated": False,
    }
    if not is_available():
        return fallback
    facts = {"mother": {"name": mother.get("name"), "age": mother.get("age"), "village": mother.get("village")},
             "vitals": vitals, "risk_score": rule_result.score, "risk_level": rule_result.level,
             "risk_factors": rule_result.factors}
    prompt = (
        f"Deterministic facts from an ASHA worker's field visit:\n{_facts_block(facts)}\n\n"
        "Return a JSON object with keys: visit_summary (2-3 sentence field-note style summary), "
        "urgency ('Low'/'Moderate'/'High'/'Critical', must match the computed risk_level), "
        "missing_data (list of any vitals fields that look absent/zero, or an empty list), "
        "follow_up_interval (1 sentence on recommended timing for next visit), "
        "ai_visit_notes (2-3 sentence note the ASHA worker could paste into her field register)."
    )
    data = generate_json(prompt)
    if not data:
        return fallback
    merged = {**fallback, **{k: v for k, v in data.items() if v}}
    merged["urgency"] = rule_result.level
    merged["ai_generated"] = True
    return merged


# ==========================================================================
# 7. DOCTOR CASE SUMMARY
# ==========================================================================
def doctor_case_summary(mother: dict, latest_assessment: dict, trend: dict) -> dict:
    fallback = {
        "case_summary": f"{mother.get('name')}, week {latest_assessment.get('week')}: "
                         f"{latest_assessment.get('risk_level')} risk (score "
                         f"{latest_assessment.get('risk_score')}/100).",
        "clinical_highlights": latest_assessment.get("risk_factors", []),
        "suggested_follow_up": latest_assessment.get("recommendation", ""),
        "suggested_investigations": "Correlate with in-person clinical exam and standard ANC labs "
                                     "as clinically indicated.",
        "patient_friendly_explanation": latest_assessment.get("recommendation", ""),
        "ai_generated": False,
    }
    if not is_available():
        return fallback
    facts = {
        "mother": {"name": mother.get("name"), "age": mother.get("age"), "village": mother.get("village"),
                   "gravida": mother.get("gravida")},
        "latest_assessment": {k: v for k, v in latest_assessment.items()
                               if k in ("week", "date", "risk_score", "risk_level", "risk_factors",
                                        "recommendation", "systolic", "diastolic", "sugar_mg_dl",
                                        "hemoglobin", "symptoms")},
        "vitals_trend_dates": trend.get("dates", []),
        "risk_score_trend": trend.get("risk_score", []),
    }
    prompt = (
        f"Deterministic case facts for a doctor reviewing a referred mother:\n{_facts_block(facts)}\n\n"
        "Return a JSON object with keys: case_summary (2-3 clinical-register sentences for the doctor), "
        "clinical_highlights (list of 3-5 short bullet strings), "
        "suggested_follow_up (1-2 sentences), "
        "suggested_investigations (1-2 sentences, general — do not name specific drugs/doses), "
        "patient_friendly_explanation (2-3 sentences the doctor could read aloud to the mother, simple language)."
    )
    data = generate_json(prompt)
    if not data:
        return fallback
    merged = {**fallback, **{k: v for k, v in data.items() if v}}
    merged["ai_generated"] = True
    return merged


# ==========================================================================
# 8. PHC / VILLAGE-LEVEL OPERATIONAL INSIGHTS
# ==========================================================================
def phc_village_insights(summary: dict, mothers: list[dict], referrals: list[dict]) -> dict:
    fallback = {
        "district_summary": f"{summary['total_mothers']} mothers tracked, "
                             f"{summary['pending_referrals']} pending referrals, "
                             f"{summary['open_alerts']} open alerts.",
        "high_risk_hotspots": [m["village"] for m in mothers][:3],
        "operational_insights": "Prioritise Critical and High risk referrals first; "
                                 "review open alerts daily.",
        "resource_recommendations": "Ensure adequate IFA tablet and BP-monitoring supply "
                                     "at the ASHA level for the villages with the most flagged mothers.",
        "ai_generated": False,
    }
    if not is_available():
        return fallback
    village_counts: dict[str, int] = {}
    for m in mothers:
        village_counts[m.get("village", "—")] = village_counts.get(m.get("village", "—"), 0) + 1
    facts = {
        "summary": summary,
        "villages_tracked": village_counts,
        "referral_urgencies": [r.get("urgency") for r in referrals],
    }
    prompt = (
        f"Deterministic PHC operational facts:\n{_facts_block(facts)}\n\n"
        "Return a JSON object with keys: district_summary (2-3 sentence executive summary), "
        "high_risk_hotspots (list of up to 3 village names or general area descriptions worth "
        "prioritising, based on the counts given), "
        "operational_insights (2-3 sentences on what PHC staff should focus on this week), "
        "resource_recommendations (1-2 sentences, general staffing/supply guidance)."
    )
    data = generate_json(prompt)
    if not data:
        return fallback
    merged = {**fallback, **{k: v for k, v in data.items() if v}}
    merged["ai_generated"] = True
    return merged


# ==========================================================================
# 9. REFERRAL PDF AI SUMMARY PARAGRAPH
# ==========================================================================
def referral_pdf_summary(mother: dict, assessment: dict, referral: dict) -> str:
    fallback = (
        f"{mother.get('name')} was assessed at {assessment.get('risk_level')} risk "
        f"(score {assessment.get('risk_score')}/100) during week {assessment.get('week')} of pregnancy. "
        f"Recommendation: {assessment.get('recommendation')}"
    )
    if not is_available():
        return fallback
    facts = {"mother": mother.get("name"), "village": mother.get("village"),
             "assessment": {k: v for k, v in assessment.items()
                             if k in ("week", "risk_score", "risk_level", "risk_factors", "recommendation")},
             "referral": {k: v for k, v in referral.items()
                          if k in ("recommended_facility", "urgency", "status")}}
    prompt = (
        f"Deterministic referral facts:\n{_facts_block(facts)}\n\n"
        "Write ONE short paragraph (3-4 sentences, clinical but readable) summarising this referral "
        "for the receiving facility, grounded only in the facts given. Return plain text, not JSON."
    )
    text = generate_text(prompt, max_tokens=250)
    return text.strip() if text else fallback
