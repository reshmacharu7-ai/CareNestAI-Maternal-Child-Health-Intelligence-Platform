"""
data/store.py
--------------
CareNest AI's entire "backend". No MySQL, no server — every role reads
and writes the SAME JSON files on disk. Because every dashboard reloads
these files fresh on every Streamlit rerun (no caching of the data
itself), an update made by an ASHA worker is immediately visible to
the Doctor / PHC / Mother the next time THEIR screen reruns (any button
click, nav change, or the manual "Refresh" button). That is what makes
the whole app feel like it is wired to one live backend, even though
it is just files.

Every list is a list[dict]. IDs are short readable strings like
"M001" (mother), "C001" (child), "A001" (assessment) etc.
"""

from __future__ import annotations

import json
import threading
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

DATA_DIR = Path(__file__).resolve().parent / "storage"
_LOCK = threading.Lock()

FILES = {
    "mothers": DATA_DIR / "mothers.json",
    "children": DATA_DIR / "children.json",
    "assessments": DATA_DIR / "assessments.json",
    "growth_records": DATA_DIR / "growth_records.json",
    "immunizations": DATA_DIR / "immunizations.json",
    "referrals": DATA_DIR / "referrals.json",
    "alerts": DATA_DIR / "alerts.json",
    "chat_history": DATA_DIR / "chat_history.json",
    "activity_log": DATA_DIR / "activity_log.json",
}


def _read(name: str) -> list[dict]:
    path = FILES[name]
    if not path.exists():
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return []


def _write(name: str, rows: list[dict]) -> None:
    path = FILES[name]
    path.parent.mkdir(parents=True, exist_ok=True)
    with _LOCK:
        tmp = path.with_suffix(".tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(rows, f, indent=2, default=str)
        tmp.replace(path)


def all_rows(name: str) -> list[dict]:
    """Always re-reads from disk -- this IS the 'live sync' mechanism."""
    return _read(name)


def get_by_id(name: str, row_id: str) -> dict | None:
    for row in _read(name):
        if row.get("id") == row_id:
            return row
    return None


def insert(name: str, row: dict) -> dict:
    rows = _read(name)
    rows.append(row)
    _write(name, rows)
    log_activity(f"{name[:-1] if name.endswith('s') else name} created: {row.get('id')}")
    return row


def update(name: str, row_id: str, patch: dict) -> dict | None:
    rows = _read(name)
    for row in rows:
        if row.get("id") == row_id:
            row.update(patch)
            _write(name, rows)
            log_activity(f"{name[:-1] if name.endswith('s') else name} updated: {row_id}")
            return row
    return None


def next_id(name: str, prefix: str) -> str:
    rows = _read(name)
    nums = [int(r["id"][len(prefix):]) for r in rows if r.get("id", "").startswith(prefix) and r["id"][len(prefix):].isdigit()]
    n = (max(nums) + 1) if nums else 1
    return f"{prefix}{n:03d}"


def log_activity(message: str) -> None:
    rows = _read("activity_log")
    rows.append({"time": datetime.now().isoformat(timespec="seconds"), "message": message})
    _write("activity_log", rows[-200:])  # keep it bounded


def recent_activity(limit: int = 8) -> list[dict]:
    return list(reversed(_read("activity_log")))[:limit]


# --------------------------------------------------------------------------
# Seeding: creates a realistic demo dataset the very first time the app
# runs, so every role's login has something meaningful to show.
# --------------------------------------------------------------------------
def _seeded() -> bool:
    return FILES["mothers"].exists()


def seed_if_empty() -> None:
    if _seeded():
        return

    today = date.today()

    mothers = [
        {
            "id": "M001", "name": "Lakshmi Devi", "age": 24, "village": "Erumaiyur",
            "phone": "9876500001", "gravida": 2, "previous_miscarriage": False,
            "lmp": str(today - timedelta(weeks=28)), "status": "pregnant",
            "asha_id": "ASHA01", "doctor_id": "DOC01", "created_at": str(today - timedelta(days=140)),
        },
        {
            "id": "M002", "name": "Fathima Beevi", "age": 32, "village": "Erumaiyur",
            "phone": "9876500002", "gravida": 3, "previous_miscarriage": True,
            "lmp": str(today - timedelta(weeks=33)), "status": "pregnant",
            "asha_id": "ASHA01", "doctor_id": "DOC01", "created_at": str(today - timedelta(days=180)),
        },
        {
            "id": "M003", "name": "Priya Ramesh", "age": 27, "village": "Erumaiyur",
            "phone": "9876500003", "gravida": 1, "previous_miscarriage": False,
            "lmp": str(today - timedelta(weeks=12)), "status": "pregnant",
            "asha_id": "ASHA01", "doctor_id": "DOC01", "created_at": str(today - timedelta(days=60)),
        },
        {
            "id": "M004", "name": "Kavitha Selvam", "age": 29, "village": "Erumaiyur",
            "phone": "9876500004", "gravida": 2, "previous_miscarriage": False,
            "lmp": str(today - timedelta(weeks=52)), "status": "postpartum",
            "asha_id": "ASHA01", "doctor_id": "DOC01", "created_at": str(today - timedelta(days=300)),
        },
    ]
    _write("mothers", mothers)

    children = [
        {
            "id": "C001", "mother_id": "M004", "name": "Baby Arun", "gender": "Male",
            "dob": str(today - timedelta(weeks=16)), "birth_weight_kg": 2.9,
        }
    ]
    _write("children", children)

    assessments = [
        {
            "id": "A001", "mother_id": "M001", "date": str(today - timedelta(days=7)),
            "week": 27, "systolic": 118, "diastolic": 76, "sugar_mg_dl": 92,
            "hemoglobin": 11.4, "weight_kg": 58, "height_cm": 158,
            "symptoms": [], "recorded_by": "ASHA Worker",
            "risk_score": 12.0, "risk_level": "Low",
            "risk_factors": ["All tracked vitals are within healthy ranges for this stage of pregnancy."],
            "recommendation": "Continue routine ANC visits and iron-folic acid supplementation.",
        },
        {
            "id": "A002", "mother_id": "M002", "date": str(today - timedelta(days=2)),
            "week": 32, "systolic": 148, "diastolic": 96, "sugar_mg_dl": 168,
            "hemoglobin": 8.9, "weight_kg": 61, "height_cm": 152,
            "symptoms": ["Swelling in hands/face", "Severe headache"], "recorded_by": "ASHA Worker",
            "risk_score": 78.0, "risk_level": "High",
            "risk_factors": [
                "Systolic BP 148 mmHg is above the safe pregnancy range (<140 mmHg) — possible pre-eclampsia.",
                "Diastolic BP 96 mmHg is above the safe range (<90 mmHg).",
                "Blood sugar 168 mg/dL suggests possible gestational diabetes.",
                "Hemoglobin 8.9 g/dL indicates moderate anemia.",
                "Reported symptom 'Swelling in hands/face' can indicate pre-eclampsia.",
                "Reported symptom 'Severe headache' can indicate pre-eclampsia.",
                "History of a previous miscarriage raises overall pregnancy risk.",
            ],
            "recommendation": "Refer to the Primary Health Centre / District Hospital promptly for BP and glucose management.",
        },
        {
            "id": "A003", "mother_id": "M003", "date": str(today - timedelta(days=10)),
            "week": 11, "systolic": 110, "diastolic": 70, "sugar_mg_dl": 88,
            "hemoglobin": 12.1, "weight_kg": 54, "height_cm": 160,
            "symptoms": ["Mild nausea"], "recorded_by": "ASHA Worker",
            "risk_score": 6.0, "risk_level": "Low",
            "risk_factors": ["All tracked vitals are within healthy ranges for this stage of pregnancy."],
            "recommendation": "Routine first-trimester care; mild nausea is common and self-limiting.",
        },
    ]
    _write("assessments", assessments)

    referrals = [
        {
            "id": "R001", "mother_id": "M002", "date": str(today - timedelta(days=2)),
            "created_by": "ASHA Worker", "risk_level": "High",
            "reasons": assessments[1]["risk_factors"],
            "recommended_facility": "Government District Hospital, Chengalpattu",
            "urgency": "Immediate (within 24 hours)", "status": "Pending Doctor Review",
        }
    ]
    _write("referrals", referrals)

    alerts = [
        {
            "id": "AL001", "mother_id": "M002", "level": "High",
            "message": "Fathima Beevi flagged HIGH risk: elevated BP, high blood sugar, low hemoglobin, pre-eclampsia symptoms.",
            "target_roles": ["asha", "doctor", "phc"],
            "created_at": str(today - timedelta(days=2)), "acknowledged": False,
        }
    ]
    _write("alerts", alerts)

    _write("growth_records", [
        {"id": "G001", "child_id": "C001", "date": str(today - timedelta(weeks=1)), "age_months": 3.5,
         "weight_kg": 5.6, "height_cm": 58.0, "muac_cm": 13.2, "notes": "Growing steadily"},
    ])

    _write("immunizations", [])
    _write("chat_history", [])
    _write("activity_log", [])
    log_activity("System seeded with demo data for Erumaiyur village.")
