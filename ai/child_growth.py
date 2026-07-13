"""
ai/child_growth.py
-------------------
AI Feature: Child Growth & Nutrition Tracking. A simplified, explainable
weight-for-age check inspired by WHO growth-standard midpoints (not a
substitute for official WHO growth charts, but enough to flag a mother
and ASHA worker toward "looks fine" vs "please get this checked").
"""

from __future__ import annotations

# age_months -> (low_kg, expected_kg, high_kg) approx WHO median band, unisex simplified
_WEIGHT_BANDS = {
    0: (2.5, 3.3, 4.0), 1: (3.4, 4.5, 5.5), 2: (4.1, 5.6, 6.6), 3: (4.6, 6.2, 7.4),
    4: (5.0, 6.7, 8.0), 6: (5.7, 7.6, 9.0), 9: (6.5, 8.6, 10.2), 12: (7.0, 9.6, 11.3),
    18: (7.9, 10.9, 12.9), 24: (8.6, 12.2, 14.3), 36: (10.0, 14.3, 16.9),
}


def _nearest_band(age_months: float) -> tuple[float, float, float]:
    key = min(_WEIGHT_BANDS.keys(), key=lambda k: abs(k - age_months))
    return _WEIGHT_BANDS[key]


def assess_growth(age_months: float, weight_kg: float | None) -> dict:
    if weight_kg is None:
        return {"status": "No data", "note": "No weight recorded yet.", "band": None}

    low, mid, high = _nearest_band(age_months)
    if weight_kg < low:
        status = "Underweight — needs attention"
        note = f"Weight {weight_kg} kg is below the expected range ({low}-{high} kg) for {age_months:.1f} months. Recommend nutrition counselling and a doctor/PHC check."
    elif weight_kg > high:
        status = "Above expected range"
        note = f"Weight {weight_kg} kg is above the typical range ({low}-{high} kg) for {age_months:.1f} months."
    else:
        status = "On track"
        note = f"Weight {weight_kg} kg is within the healthy range ({low}-{high} kg) for {age_months:.1f} months."
    return {"status": status, "note": note, "band": (low, mid, high)}
