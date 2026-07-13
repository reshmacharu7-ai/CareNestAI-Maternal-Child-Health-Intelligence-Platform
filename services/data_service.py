"""
services/data_service.py
-------------------------
Business logic sitting on top of data.store. Every dashboard imports
from HERE, never from data.store directly, so risk-scoring, alerting
and referral rules only live in one place.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta

from ai.risk_model import assess_risk
from data import store


# ---------------------------------------------------------------- mothers --
def list_mothers() -> list[dict]:
    return store.all_rows("mothers")


def get_mother(mother_id: str) -> dict | None:
    return store.get_by_id("mothers", mother_id)


def register_mother(data: dict) -> dict:
    row = {
        "id": store.next_id("mothers", "M"),
        "created_at": str(date.today()),
        "status": "pregnant",
        **data,
    }
    return store.insert("mothers", row)


def pregnancy_week(mother: dict) -> int:
    if not mother.get("lmp"):
        return 0
    lmp = datetime.strptime(mother["lmp"], "%Y-%m-%d").date()
    return max(0, (date.today() - lmp).days // 7)


# ------------------------------------------------------------ assessments --
def list_assessments(mother_id: str | None = None) -> list[dict]:
    rows = store.all_rows("assessments")
    if mother_id:
        rows = [r for r in rows if r["mother_id"] == mother_id]
    return sorted(rows, key=lambda r: r["date"])


def latest_assessment(mother_id: str) -> dict | None:
    rows = list_assessments(mother_id)
    return rows[-1] if rows else None


def record_assessment(mother_id: str, vitals: dict, recorded_by: str) -> dict:
    """Runs the AI risk model, saves the assessment, and — if High/Critical
    — automatically creates a referral + alert so every downstream role
    (ASHA, Doctor, PHC) sees it the moment their screen refreshes."""
    mother = get_mother(mother_id)
    week = vitals.get("week") or pregnancy_week(mother)
    result = assess_risk({**vitals, "week": week, "age": mother.get("age"),
                           "previous_miscarriage": mother.get("previous_miscarriage", False)})

    row = {
        "id": store.next_id("assessments", "A"),
        "mother_id": mother_id,
        "date": str(date.today()),
        "week": week,
        "recorded_by": recorded_by,
        "risk_score": result.score,
        "risk_level": result.level,
        "risk_factors": result.factors,
        "recommendation": result.recommendation,
        "referral_urgency": result.referral_urgency,
        **vitals,
    }
    store.insert("assessments", row)

    if result.level in ("High", "Critical"):
        create_referral(mother_id, result, created_by=recorded_by)
        create_alert(mother_id, result)

    return row


def trend_data(mother_id: str) -> dict:
    rows = list_assessments(mother_id)
    return {
        "dates": [r["date"] for r in rows],
        "systolic": [r.get("systolic") for r in rows],
        "diastolic": [r.get("diastolic") for r in rows],
        "sugar": [r.get("sugar_mg_dl") for r in rows],
        "hemoglobin": [r.get("hemoglobin") for r in rows],
        "weight": [r.get("weight_kg") for r in rows],
        "risk_score": [r.get("risk_score") for r in rows],
    }


# -------------------------------------------------------------- referrals --
def create_referral(mother_id: str, result, created_by: str, facility: str | None = None) -> dict:
    urgency = "Immediate (within 24 hours)" if result.level == "Critical" else "Urgent (within 2-3 days)"
    row = {
        "id": store.next_id("referrals", "R"),
        "mother_id": mother_id,
        "date": str(date.today()),
        "created_by": created_by,
        "risk_level": result.level,
        "reasons": result.factors,
        "recommended_facility": facility or "Primary Health Centre, Erumaiyur",
        "urgency": urgency,
        "status": "Pending Doctor Review",
    }
    return store.insert("referrals", row)


def list_referrals(mother_id: str | None = None, status: str | None = None) -> list[dict]:
    rows = store.all_rows("referrals")
    if mother_id:
        rows = [r for r in rows if r["mother_id"] == mother_id]
    if status:
        rows = [r for r in rows if r["status"] == status]
    return sorted(rows, key=lambda r: r["date"], reverse=True)


def update_referral_status(referral_id: str, status: str) -> dict | None:
    return store.update("referrals", referral_id, {"status": status})


# ----------------------------------------------------------------- alerts --
def create_alert(mother_id: str, result) -> dict:
    mother = get_mother(mother_id)
    row = {
        "id": store.next_id("alerts", "AL"),
        "mother_id": mother_id,
        "level": result.level,
        "message": f"{mother['name']} flagged {result.level.upper()} risk: "
                   f"{'; '.join(result.factors[:3])}",
        "target_roles": ["asha", "doctor", "phc"],
        "created_at": str(date.today()),
        "acknowledged": False,
    }
    return store.insert("alerts", row)


def list_alerts(unacknowledged_only: bool = False) -> list[dict]:
    rows = store.all_rows("alerts")
    if unacknowledged_only:
        rows = [r for r in rows if not r.get("acknowledged")]
    return sorted(rows, key=lambda r: r["created_at"], reverse=True)


def acknowledge_alert(alert_id: str) -> dict | None:
    return store.update("alerts", alert_id, {"acknowledged": True})


# --------------------------------------------------------------- children --
def list_children(mother_id: str | None = None) -> list[dict]:
    rows = store.all_rows("children")
    if mother_id:
        rows = [r for r in rows if r["mother_id"] == mother_id]
    return rows


def register_child(mother_id: str, data: dict) -> dict:
    row = {"id": store.next_id("children", "C"), "mother_id": mother_id, **data}
    store.insert("children", row)
    store.update("mothers", mother_id, {"status": "postpartum"})
    return row


def child_age_months(child: dict) -> float:
    dob = datetime.strptime(child["dob"], "%Y-%m-%d").date()
    return round((date.today() - dob).days / 30.44, 1)


def list_growth_records(child_id: str) -> list[dict]:
    rows = [r for r in store.all_rows("growth_records") if r["child_id"] == child_id]
    return sorted(rows, key=lambda r: r["date"])


def record_growth(child_id: str, data: dict) -> dict:
    row = {
        "id": store.next_id("growth_records", "G"),
        "child_id": child_id,
        "date": str(date.today()),
        **data,
    }
    return store.insert("growth_records", row)


def village_summary() -> dict:
    mothers = list_mothers()
    assessments = store.all_rows("assessments")
    latest_by_mother: dict[str, dict] = {}
    for a in sorted(assessments, key=lambda r: r["date"]):
        latest_by_mother[a["mother_id"]] = a
    risk_counts = {"Low": 0, "Moderate": 0, "High": 0, "Critical": 0}
    for m in mothers:
        latest = latest_by_mother.get(m["id"])
        level = latest["risk_level"] if latest else "Low"
        risk_counts[level] = risk_counts.get(level, 0) + 1
    return {
        "total_mothers": len(mothers),
        "pregnant": sum(1 for m in mothers if m.get("status") == "pregnant"),
        "postpartum": sum(1 for m in mothers if m.get("status") == "postpartum"),
        "total_children": len(list_children()),
        "risk_counts": risk_counts,
        "pending_referrals": len(list_referrals(status="Pending Doctor Review")),
        "open_alerts": len(list_alerts(unacknowledged_only=True)),
    }
