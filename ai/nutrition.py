"""
ai/nutrition.py
----------------
AI Feature: Personalized Nutrition Planner. Deterministic, explainable
rules grounded in the mother's own latest vitals -- no invented advice.
"""

from __future__ import annotations


def nutrition_plan(mother: dict, latest_assessment: dict | None, week: int) -> list[dict]:
    plan = []

    if week < 13:
        stage = "first trimester"
    elif week < 27:
        stage = "second trimester"
    else:
        stage = "third trimester"

    plan.append({
        "title": "Folic acid & iron",
        "why": "Reduces risk of neural tube defects and supports the extra blood volume of pregnancy.",
        "foods": "Continue the daily iron-folic acid (IFA) tablet from the ASHA worker; leafy greens, jaggery, dates.",
    })

    hb = (latest_assessment or {}).get("hemoglobin")
    if hb is not None and hb < 11:
        plan.append({
            "title": "Extra iron-rich foods (anemia detected)",
            "why": f"Hemoglobin {hb} g/dL is below the healthy pregnancy threshold (11 g/dL).",
            "foods": "Ragi, spinach, drumstick leaves, jaggery, eggs, and a vitamin-C food (amla/orange) with every meal to help absorb iron.",
        })

    sugar = (latest_assessment or {}).get("sugar_mg_dl")
    if sugar is not None and sugar > 140:
        plan.append({
            "title": "Lower-glycemic meals (elevated sugar detected)",
            "why": f"Blood sugar {sugar} mg/dL is above the healthy range; smaller, balanced meals help control it.",
            "foods": "Whole grains (millets/brown rice) over polished rice, more vegetables, smaller frequent meals, avoid sugary drinks/sweets.",
        })

    bp = (latest_assessment or {}).get("systolic")
    if bp is not None and bp >= 130:
        plan.append({
            "title": "Lower-salt meals (elevated BP detected)",
            "why": f"Systolic BP {bp} mmHg is elevated; reducing salt/oily food helps manage it.",
            "foods": "Reduce added salt and pickles; more fruit, buttermilk, and water; avoid fried snacks.",
        })

    plan.append({
        "title": f"Calorie & protein needs for the {stage}",
        "why": "Energy and protein needs rise as the baby grows.",
        "foods": "Add one extra balanced meal a day (rice/millet + dal + vegetable + curd), plus a glass of milk if available.",
    })

    plan.append({
        "title": "Calcium",
        "why": "Supports the baby's bone development and the mother's own bone health.",
        "foods": "Milk, curd, ragi, sesame (til) seeds — take calcium tablets at a different time from the IFA tablet.",
    })

    return plan
