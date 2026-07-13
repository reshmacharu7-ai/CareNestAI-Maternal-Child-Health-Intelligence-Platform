"""
ai/schedule.py
---------------
AI Features: Personalized Pregnancy Timeline + Follow-up Schedule +
Child Immunization Schedule. All deterministic (no AI needed for a
fixed medical schedule) but presented as part of the AI companion
experience, exactly like a real ANC/immunization calendar would be.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta

ANC_VISIT_WEEKS = [12, 20, 26, 30, 34, 36, 38, 40]

PREGNANCY_MILESTONES = [
    (12, "First trimester screening / dating scan"),
    (18, "Anomaly scan window opens"),
    (20, "Anomaly (Level II) ultrasound scan"),
    (24, "Glucose tolerance test (gestational diabetes screening)"),
    (28, "Tetanus toxoid 2nd dose (if not already given)"),
    (30, "Growth scan"),
    (36, "Position check / birth preparedness counselling"),
    (40, "Expected delivery window begins"),
]

CHILD_IMMUNIZATION_SCHEDULE = [
    (0, "BCG, OPV-0, Hepatitis B (birth dose)"),
    (1.5, "OPV-1, Pentavalent-1, Rotavirus-1, PCV-1"),
    (2.5, "OPV-2, Pentavalent-2, Rotavirus-2, PCV-2"),
    (3.5, "OPV-3, Pentavalent-3, Rotavirus-3, PCV-3"),
    (9, "Measles-Rubella (MR)-1, Vitamin A (1st dose)"),
    (12, "PCV Booster"),
    (16, "MR-2, DPT Booster-1, OPV Booster"),
    (24, "Vitamin A (2nd dose)"),
]

CHILD_MILESTONES = [
    (2, "Smiles responsively, follows objects with eyes"),
    (4, "Holds head steady, coos and babbles"),
    (6, "Sits with support, starts semi-solid food"),
    (9, "Crawls, responds to name"),
    (12, "Stands with support, says 1-2 words, pincer grasp"),
    (18, "Walks independently, says several words"),
    (24, "Runs, forms 2-word phrases, points to body parts"),
    (36, "Speaks in short sentences, plays with other children"),
]


def pregnancy_timeline(mother: dict, current_week: int) -> list[dict]:
    lmp = datetime.strptime(mother["lmp"], "%Y-%m-%d").date()
    edd = lmp + timedelta(weeks=40)
    items = []
    for w, label in PREGNANCY_MILESTONES:
        target_date = lmp + timedelta(weeks=w)
        status = "done" if w < current_week else ("current" if w <= current_week + 2 else "upcoming")
        items.append({"week": w, "label": label, "date": str(target_date), "status": status})
    return {"edd": str(edd), "items": items}


def next_anc_visit(current_week: int) -> int | None:
    for w in ANC_VISIT_WEEKS:
        if w >= current_week:
            return w
    return None


def child_immunization_plan(child: dict) -> list[dict]:
    dob = datetime.strptime(child["dob"], "%Y-%m-%d").date()
    age_months = (date.today() - dob).days / 30.44
    items = []
    for m, label in CHILD_IMMUNIZATION_SCHEDULE:
        due_date = dob + timedelta(days=int(m * 30.44))
        if m < age_months - 1:
            status = "overdue" if m < age_months - 1.5 else "done"
        elif m <= age_months:
            status = "done"
        elif m <= age_months + 1:
            status = "due soon"
        else:
            status = "upcoming"
        items.append({"age_months": m, "vaccines": label, "due_date": str(due_date), "status": status})
    return items


def child_milestone_checklist(child: dict) -> list[dict]:
    dob = datetime.strptime(child["dob"], "%Y-%m-%d").date()
    age_months = (date.today() - dob).days / 30.44
    items = []
    for m, label in CHILD_MILESTONES:
        expected = "expected by now" if m <= age_months else "upcoming"
        items.append({"age_months": m, "milestone": label, "expected": expected})
    return items
