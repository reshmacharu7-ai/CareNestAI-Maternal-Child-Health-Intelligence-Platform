"""
ai/risk_model.py
-----------------
AI Feature 1: Explainable Maternal Risk Prediction.

Same honest approach as the original cardiac model this project is
based on: a transparent, clinically-informed rule-based score built
from published maternal-health reference ranges (WHO / ACOG pregnancy
BP, glucose and hemoglobin thresholds), so every point on the score is
traceable to one specific vital or symptom. This is a screening aid,
never a diagnosis -- every High/Critical result tells the mother to
see a doctor.
"""

from __future__ import annotations

from dataclasses import dataclass, field

CRITICAL_SYMPTOMS = {
    "severe headache": "can indicate pre-eclampsia.",
    "blurred vision": "can indicate pre-eclampsia.",
    "swelling in hands/face": "can indicate pre-eclampsia.",
    "reduced fetal movement": "can indicate fetal distress and needs urgent review.",
    "vaginal bleeding": "can indicate a serious pregnancy complication.",
    "high fever": "can indicate infection needing prompt treatment.",
    "severe abdominal pain": "can indicate a serious complication.",
}
MINOR_SYMPTOMS = {"mild nausea", "mild fatigue", "back pain", "mild swelling in feet"}


@dataclass
class RiskAssessment:
    score: float
    level: str
    factors: list[str] = field(default_factory=list)
    recommendation: str = ""
    referral_urgency: str = "Routine"


def _penalty(value, low, high, weight) -> tuple[float, bool]:
    if value is None:
        return 0.0, False
    if low <= value <= high:
        return 0.0, False
    distance = (low - value) if value < low else (value - high)
    span = max(high - low, 1e-6)
    severity = min(distance / span, 2.0)
    return weight * (1 + severity), True


def assess_risk(vitals: dict) -> RiskAssessment:
    points = 0.0
    factors: list[str] = []

    age = vitals.get("age")
    if age is not None and (age < 18 or age > 35):
        points += 8
        factors.append(f"Maternal age {age} is outside the lowest-risk range (18-35 years).")

    week = vitals.get("week")

    sys_bp = vitals.get("systolic")
    p, hit = _penalty(sys_bp, 90, 139, 14)
    if hit:
        points += p
        factors.append(f"Systolic BP {sys_bp} mmHg is above/below the safe pregnancy range (90-139 mmHg) — possible hypertension/pre-eclampsia.")

    dia_bp = vitals.get("diastolic")
    p, hit = _penalty(dia_bp, 60, 89, 12)
    if hit:
        points += p
        factors.append(f"Diastolic BP {dia_bp} mmHg is above/below the safe range (60-89 mmHg).")

    sugar = vitals.get("sugar_mg_dl")
    p, hit = _penalty(sugar, 70, 140, 12)
    if hit:
        points += p
        factors.append(f"Blood sugar {sugar} mg/dL is outside the healthy range (70-140 mg/dL) — possible gestational diabetes.")

    hb = vitals.get("hemoglobin")
    if hb is not None:
        if hb < 7:
            points += 30
            factors.append(f"Hemoglobin {hb} g/dL indicates SEVERE anemia — needs urgent attention.")
        elif hb < 11:
            points += 15
            factors.append(f"Hemoglobin {hb} g/dL indicates anemia (WHO pregnancy threshold: 11 g/dL).")

    weight = vitals.get("weight_kg")
    height = vitals.get("height_cm")
    if weight and height:
        bmi = weight / ((height / 100) ** 2)
        if bmi < 18.5:
            points += 8
            factors.append(f"BMI {bmi:.1f} suggests undernutrition — needs nutrition support.")
        elif bmi >= 30:
            points += 8
            factors.append(f"BMI {bmi:.1f} suggests obesity — raises risk of gestational diabetes/hypertension.")

    symptoms = [s.strip().lower() for s in (vitals.get("symptoms") or [])]
    for s in symptoms:
        if s in CRITICAL_SYMPTOMS:
            points += 18
            factors.append(f"Reported symptom '{s.title()}' {CRITICAL_SYMPTOMS[s]}")
        elif s in MINOR_SYMPTOMS:
            points += 2

    if vitals.get("previous_miscarriage"):
        points += 10
        factors.append("History of a previous miscarriage raises overall pregnancy risk.")

    if week is not None and week >= 41:
        points += 10
        factors.append(f"Pregnancy week {week} is post-term (≥41 weeks) — needs prompt medical review.")

    score = round(min(points, 100.0), 1)

    if score < 20:
        level, rec, urgency = "Low", "Vitals look healthy for this stage of pregnancy. Continue routine ANC visits.", "Routine"
    elif score < 40:
        level, rec, urgency = "Moderate", "A few readings are drifting outside the healthy range. Book a follow-up with the doctor within a week.", "Follow-up (within a week)"
    elif score < 65:
        level, rec, urgency = "High", "Multiple readings are concerning. Refer to a doctor / PHC promptly.", "Urgent (within 2-3 days)"
    else:
        level, rec, urgency = "Critical", "Several vitals are significantly abnormal. Refer immediately — do not wait.", "Immediate (within 24 hours)"

    if not factors:
        factors = ["All tracked vitals are within healthy ranges for this stage of pregnancy."]

    return RiskAssessment(score=score, level=level, factors=factors, recommendation=rec, referral_urgency=urgency)
