# CareNest AI

**Early Detection. Smarter Decisions. Safer Mothers. Healthier Babies.**

A rebrand + feature-extension of your original **SmartCare AI+** Streamlit
project into an AI-powered maternal & child health platform — built as a
**prototype only** (no MySQL, no separate backend server). The dark
glassmorphism theme, ECG pulse animation, gradient text, glass cards,
risk badges and chat bubbles are the exact same CSS from SmartCare AI+
(`assets/css/style.css` is untouched apart from the title string).

## Run it

```bash
pip install -r requirements.txt
streamlit run app.py
```

First run auto-seeds `data/storage/*.json` with a realistic demo village
(4 mothers, 1 child, 3 assessments, 1 referral, 1 alert) — delete that
folder any time to reset the demo.

## How the "connected backend" illusion works

There is no server. `data/store.py` reads/writes plain JSON files on
disk. Every dashboard re-reads those files on **every** Streamlit
rerun (no caching of the data itself), so when an ASHA worker records
an assessment, the mother's own dashboard, the Doctor's referral queue
and the PHC's priority list all show it the next time their screen
reruns (any click, nav change, or the sidebar "🔄 Refresh live data"
button). A High/Critical risk result also automatically creates a
referral + a cross-role alert banner — that's the "looks real-time"
trick.

## Roles & demo logins

All shown directly on the landing/login screen, one tab per role:

| Role | Email | Password |
|---|---|---|
| Pregnant Woman/Mother | lakshmi@demo.in | demo123 |
| Pregnant Woman/Mother | fathima@demo.in (seeded High-risk case) | demo123 |
| Pregnant Woman/Mother | priya@demo.in | demo123 |
| Pregnant Woman/Mother | kavitha@demo.in (has a registered child) | demo123 |
| ASHA Worker | asha@demo.in | asha123 |
| Doctor | doctor@demo.in | doc123 |
| Primary Health Centre | phc@demo.in | phc123 |

## The 8 AI features

1. **Explainable Maternal Risk Prediction** — `ai/risk_model.py`, transparent rule-based score (WHO/ACOG-style BP, glucose, hemoglobin thresholds) with Low/Moderate/High/Critical output and a plain-language reason for every point.
2. **Personalized Nutrition Planner** — `ai/nutrition.py`, grounded in the mother's own latest vitals.
3. **Personalized Pregnancy Timeline** — `ai/schedule.py`, built from LMP: ANC visits, scans, EDD.
4. **AI Referral PDF** — `services/pdf_service.py` (reportlab), downloadable from the Doctor dashboard.
5. **Smart Alert System** — auto-fires on High/Critical, visible to ASHA/Doctor/PHC via the alert banner.
6. **Trend Analysis** — `graphs/trend_charts.py` (Plotly) + a deterministic improving/worsening summary.
7. **Child Growth, Milestones & Immunization Tracking** — `ai/child_growth.py` + `ai/schedule.py`.
8. **AI Health Companion chatbot** — `ai/chatbot.py`, keyword-grounded Q&A with a crisis-safety guard, works fully offline (no API key needed).

## What was intentionally left out of this pass

Voice input and OCR report scanning (features 2 & 3 of your original
brief) need extra heavy dependencies (speech recognition / EasyOCR)
that don't reliably run in every environment — they were left out so
the rest of the app stays 100% runnable out of the box. If you want
them added with graceful "manual entry" fallback, that's a
straightforward follow-up.
