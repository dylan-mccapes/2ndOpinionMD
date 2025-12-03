# server/api/eoh_demo_data.py
"""
In-memory demo registry for four synthetic RA patients.
These are not persisted anywhere; they're just Python structures for the EoH demo.
"""

from __future__ import annotations

from typing import Dict, Any, List, TypedDict


class DemoPatient(TypedDict):
    id: str
    label: str
    summary: str
    diagnosis: str
    age: int
    sex: str
    serostatus: str
    meds: List[Dict[str, Any]]
    recent_labs: List[Dict[str, Any]]
    das28_history: List[Dict[str, Any]]
    recent_flares: List[Dict[str, Any]]
    journal_highlights: List[str]


class DemoEvent(TypedDict):
    ts: str  # ISO 8601
    kind: str  # "visit", "flare", "lab", "med_change", "journal"
    summary: str
    details: Dict[str, Any]


# ---------------------------------------------------------------------------
# Patient 1: Recurrent moderate flares, currently controlled
# 38F, seropositive RA, on MTX + adalimumab
# DAS28: high -> moderate -> low
# 2 moderate flares in last 12 months
# ---------------------------------------------------------------------------

P1_PATIENT: DemoPatient = {
    "id": "P1",
    "label": "P1 - Recurrent flares on MTX + ADA",
    "summary": "38F with seropositive RA, 2 moderate flares in past 12 months, now in low disease activity on MTX + adalimumab",
    "diagnosis": "Seropositive rheumatoid arthritis (RF+, anti-CCP+)",
    "age": 38,
    "sex": "F",
    "serostatus": "seropositive",
    "meds": [
        {"name": "methotrexate", "dose": "15 mg", "frequency": "weekly", "start_date": "2024-01-15", "status": "ongoing"},
        {"name": "folic_acid", "dose": "1 mg", "frequency": "daily", "start_date": "2024-01-15", "status": "ongoing"},
        {"name": "adalimumab", "dose": "40 mg", "frequency": "q2w", "start_date": "2024-04-01", "status": "ongoing"},
    ],
    "recent_labs": [
        {"date": "2025-07-15", "CRP": 4.2, "ESR": 18, "RF": 85, "anti_CCP": 120},
        {"date": "2025-04-10", "CRP": 28.0, "ESR": 52, "RF": 92, "anti_CCP": 125},
        {"date": "2025-01-20", "CRP": 8.5, "ESR": 28, "RF": 88, "anti_CCP": 118},
    ],
    "das28_history": [
        {"date": "2025-07-15", "das28": 2.8, "category": "low_activity"},
        {"date": "2025-04-10", "das28": 4.6, "category": "moderate_activity"},
        {"date": "2025-01-20", "das28": 3.4, "category": "moderate_activity"},
        {"date": "2024-10-15", "das28": 5.2, "category": "high_activity"},
        {"date": "2024-04-01", "das28": 5.8, "category": "high_activity"},
    ],
    "recent_flares": [
        {"date": "2025-04-08", "severity": "moderate", "joints": ["MCPs", "PIPs", "wrists"], "duration_days": 12},
        {"date": "2024-11-20", "severity": "moderate", "joints": ["knees", "ankles"], "duration_days": 10},
    ],
    "journal_highlights": [
        "Work stress seems to trigger more stiffness",
        "Morning stiffness usually 30-45 min on good days",
        "Hands ache more after long typing sessions",
        "Sleep quality improved since starting adalimumab",
    ],
}

P1_TIMELINE: List[DemoEvent] = [
    {
        "ts": "2024-01-15T09:00:00Z",
        "kind": "visit",
        "summary": "Initial rheumatology visit - seropositive RA diagnosed",
        "details": {"das28": 5.8, "swollen_joints": 12, "tender_joints": 18, "morning_stiffness_min": 120, "RF_positive": True, "anti_CCP_positive": True},
    },
    {
        "ts": "2024-01-15T10:00:00Z",
        "kind": "med_change",
        "summary": "Start methotrexate 15 mg weekly + folic acid",
        "details": {"medication": "methotrexate", "dose": "15 mg", "frequency": "weekly", "action": "start"},
    },
    {
        "ts": "2024-01-15T11:00:00Z",
        "kind": "lab",
        "summary": "Baseline labs - elevated inflammatory markers",
        "details": {"CRP": 42.0, "ESR": 68, "RF": 95, "anti_CCP": 130, "CBC": "normal", "LFTs": "normal"},
    },
    {
        "ts": "2024-02-20T20:00:00Z",
        "kind": "journal",
        "summary": "Feeling overwhelmed with new diagnosis",
        "details": {"mood": "anxious", "pain_level": 7, "text": "Just got diagnosed with RA. Scared about what this means for my future. Hands hurt constantly."},
    },
    {
        "ts": "2024-03-15T09:00:00Z",
        "kind": "visit",
        "summary": "6-week follow-up - partial response to MTX",
        "details": {"das28": 5.2, "swollen_joints": 8, "tender_joints": 14, "morning_stiffness_min": 90},
    },
    {
        "ts": "2024-03-15T10:00:00Z",
        "kind": "lab",
        "summary": "Labs improving but still elevated",
        "details": {"CRP": 28.0, "ESR": 48, "LFTs": "normal"},
    },
    {
        "ts": "2024-04-01T09:00:00Z",
        "kind": "med_change",
        "summary": "Add adalimumab 40 mg q2w due to inadequate response",
        "details": {"medication": "adalimumab", "dose": "40 mg", "frequency": "q2w", "action": "start", "reason": "inadequate_response_to_csDMARD"},
    },
    {
        "ts": "2024-04-15T21:00:00Z",
        "kind": "journal",
        "summary": "First adalimumab injection went well",
        "details": {"mood": "hopeful", "pain_level": 5, "text": "Did my first Humira shot today. Nurse showed me how. Wasn't as bad as I expected. Hoping this helps."},
    },
    {
        "ts": "2024-05-15T09:00:00Z",
        "kind": "visit",
        "summary": "Good response to combination therapy",
        "details": {"das28": 4.2, "swollen_joints": 4, "tender_joints": 8, "morning_stiffness_min": 45},
    },
    {
        "ts": "2024-05-15T10:00:00Z",
        "kind": "lab",
        "summary": "Inflammatory markers improving",
        "details": {"CRP": 12.0, "ESR": 32, "LFTs": "normal"},
    },
    {
        "ts": "2024-07-10T09:00:00Z",
        "kind": "visit",
        "summary": "Continued improvement - approaching low disease activity",
        "details": {"das28": 3.6, "swollen_joints": 2, "tender_joints": 5, "morning_stiffness_min": 30},
    },
    {
        "ts": "2024-08-20T22:00:00Z",
        "kind": "journal",
        "summary": "Feeling much better overall",
        "details": {"mood": "positive", "pain_level": 3, "text": "Best I've felt in months. Morning stiffness is way down. Can type for longer without pain."},
    },
    {
        "ts": "2024-10-15T09:00:00Z",
        "kind": "visit",
        "summary": "Routine follow-up - stable low-moderate activity",
        "details": {"das28": 3.2, "swollen_joints": 1, "tender_joints": 4, "morning_stiffness_min": 25},
    },
    {
        "ts": "2024-10-15T10:00:00Z",
        "kind": "lab",
        "summary": "Labs near normal",
        "details": {"CRP": 6.0, "ESR": 22, "LFTs": "normal"},
    },
    {
        "ts": "2024-11-18T21:00:00Z",
        "kind": "journal",
        "summary": "Knees starting to hurt more",
        "details": {"mood": "worried", "pain_level": 5, "text": "Knees have been bothering me the past few days. Hope it's not a flare coming on. Work has been stressful."},
    },
    {
        "ts": "2024-11-20T08:00:00Z",
        "kind": "flare",
        "summary": "Moderate flare - knees and ankles",
        "details": {"severity": "moderate", "joints": ["knees", "ankles"], "morning_stiffness_min": 90, "trigger": "work_stress"},
    },
    {
        "ts": "2024-11-20T14:00:00Z",
        "kind": "med_change",
        "summary": "Prednisone burst for flare",
        "details": {"medication": "prednisone", "dose": "20 mg", "frequency": "daily", "duration": "7 days taper", "action": "start"},
    },
    {
        "ts": "2024-11-20T15:00:00Z",
        "kind": "lab",
        "summary": "Labs during flare - elevated markers",
        "details": {"CRP": 32.0, "ESR": 58},
    },
    {
        "ts": "2024-12-01T09:00:00Z",
        "kind": "visit",
        "summary": "Post-flare follow-up - improving",
        "details": {"das28": 4.0, "swollen_joints": 3, "tender_joints": 6, "morning_stiffness_min": 50},
    },
    {
        "ts": "2025-01-20T09:00:00Z",
        "kind": "visit",
        "summary": "Routine visit - back to low-moderate activity",
        "details": {"das28": 3.4, "swollen_joints": 2, "tender_joints": 4, "morning_stiffness_min": 35},
    },
    {
        "ts": "2025-01-20T10:00:00Z",
        "kind": "lab",
        "summary": "Labs improved post-flare",
        "details": {"CRP": 8.5, "ESR": 28, "RF": 88, "anti_CCP": 118},
    },
    {
        "ts": "2025-02-15T20:00:00Z",
        "kind": "journal",
        "summary": "Doing well, managing stress better",
        "details": {"mood": "good", "pain_level": 2, "text": "Started yoga and it seems to help with stress. Hands feel pretty good most days."},
    },
    {
        "ts": "2025-04-05T21:00:00Z",
        "kind": "journal",
        "summary": "Hands feeling stiff again",
        "details": {"mood": "concerned", "pain_level": 5, "text": "Woke up with really stiff hands today. Took over an hour to loosen up. Big deadline at work this week."},
    },
    {
        "ts": "2025-04-08T07:00:00Z",
        "kind": "flare",
        "summary": "Moderate flare - MCPs, PIPs, wrists",
        "details": {"severity": "moderate", "joints": ["MCPs", "PIPs", "wrists"], "morning_stiffness_min": 120, "trigger": "work_deadline_stress"},
    },
    {
        "ts": "2025-04-08T14:00:00Z",
        "kind": "med_change",
        "summary": "Prednisone burst for second flare",
        "details": {"medication": "prednisone", "dose": "15 mg", "frequency": "daily", "duration": "5 days taper", "action": "start"},
    },
    {
        "ts": "2025-04-10T09:00:00Z",
        "kind": "visit",
        "summary": "Urgent visit during flare",
        "details": {"das28": 4.6, "swollen_joints": 6, "tender_joints": 10, "morning_stiffness_min": 100},
    },
    {
        "ts": "2025-04-10T10:00:00Z",
        "kind": "lab",
        "summary": "Labs elevated during flare",
        "details": {"CRP": 28.0, "ESR": 52, "RF": 92, "anti_CCP": 125},
    },
    {
        "ts": "2025-04-25T20:00:00Z",
        "kind": "journal",
        "summary": "Flare resolving, feeling better",
        "details": {"mood": "relieved", "pain_level": 3, "text": "Prednisone helped a lot. Swelling going down. Need to figure out how to manage work stress better."},
    },
    {
        "ts": "2025-05-20T09:00:00Z",
        "kind": "visit",
        "summary": "Post-flare follow-up - good recovery",
        "details": {"das28": 3.2, "swollen_joints": 2, "tender_joints": 4, "morning_stiffness_min": 40},
    },
    {
        "ts": "2025-07-15T09:00:00Z",
        "kind": "visit",
        "summary": "Routine visit - low disease activity achieved",
        "details": {"das28": 2.8, "swollen_joints": 1, "tender_joints": 2, "morning_stiffness_min": 30},
    },
    {
        "ts": "2025-07-15T10:00:00Z",
        "kind": "lab",
        "summary": "Labs near normal - best since diagnosis",
        "details": {"CRP": 4.2, "ESR": 18, "RF": 85, "anti_CCP": 120, "LFTs": "normal"},
    },
    {
        "ts": "2025-08-01T21:00:00Z",
        "kind": "journal",
        "summary": "Feeling stable, cautiously optimistic",
        "details": {"mood": "hopeful", "pain_level": 2, "text": "Best I've felt in a while. Morning stiffness usually under 30 min. Trying to keep stress in check."},
    },
]


# ---------------------------------------------------------------------------
# Patient 2: Deep remission / very low risk
# 42F, seropositive RA, early aggressive therapy, sustained remission
# No flares in 18-24 months
# DAS28 near remission (<2.6) for >18 months
# ---------------------------------------------------------------------------

P2_PATIENT: DemoPatient = {
    "id": "P2",
    "label": "P2 - Deep remission",
    "summary": "42F with seropositive RA in sustained remission for 20+ months on MTX + etanercept, no flares",
    "diagnosis": "Seropositive rheumatoid arthritis (RF+, anti-CCP+) - in remission",
    "age": 42,
    "sex": "F",
    "serostatus": "seropositive",
    "meds": [
        {"name": "methotrexate", "dose": "12.5 mg", "frequency": "weekly", "start_date": "2022-06-01", "status": "ongoing"},
        {"name": "folic_acid", "dose": "1 mg", "frequency": "daily", "start_date": "2022-06-01", "status": "ongoing"},
        {"name": "etanercept", "dose": "50 mg", "frequency": "weekly", "start_date": "2022-09-15", "status": "ongoing"},
    ],
    "recent_labs": [
        {"date": "2025-08-01", "CRP": 1.2, "ESR": 8, "RF": 45, "anti_CCP": 65},
        {"date": "2025-05-01", "CRP": 1.5, "ESR": 10, "RF": 48, "anti_CCP": 68},
        {"date": "2025-02-01", "CRP": 1.8, "ESR": 12, "RF": 50, "anti_CCP": 70},
    ],
    "das28_history": [
        {"date": "2025-08-01", "das28": 1.8, "category": "remission"},
        {"date": "2025-05-01", "das28": 2.0, "category": "remission"},
        {"date": "2025-02-01", "das28": 2.2, "category": "remission"},
        {"date": "2024-11-01", "das28": 2.1, "category": "remission"},
        {"date": "2024-08-01", "das28": 2.3, "category": "remission"},
        {"date": "2024-05-01", "das28": 2.4, "category": "remission"},
    ],
    "recent_flares": [],
    "journal_highlights": [
        "Feeling great, barely any stiffness most days",
        "Can do all my normal activities without limitation",
        "Grateful for early treatment",
        "Only occasional mild achiness, usually weather-related",
    ],
}

P2_TIMELINE: List[DemoEvent] = [
    {
        "ts": "2022-06-01T09:00:00Z",
        "kind": "visit",
        "summary": "Initial diagnosis - early RA caught on screening",
        "details": {"das28": 4.8, "swollen_joints": 6, "tender_joints": 10, "morning_stiffness_min": 75, "RF_positive": True, "anti_CCP_positive": True},
    },
    {
        "ts": "2022-06-01T10:00:00Z",
        "kind": "med_change",
        "summary": "Start methotrexate 15 mg weekly - early aggressive approach",
        "details": {"medication": "methotrexate", "dose": "15 mg", "frequency": "weekly", "action": "start"},
    },
    {
        "ts": "2022-06-01T11:00:00Z",
        "kind": "lab",
        "summary": "Baseline labs",
        "details": {"CRP": 25.0, "ESR": 42, "RF": 78, "anti_CCP": 95},
    },
    {
        "ts": "2022-08-15T09:00:00Z",
        "kind": "visit",
        "summary": "Good initial response to MTX",
        "details": {"das28": 3.8, "swollen_joints": 3, "tender_joints": 6, "morning_stiffness_min": 45},
    },
    {
        "ts": "2022-09-15T09:00:00Z",
        "kind": "med_change",
        "summary": "Add etanercept for treat-to-target approach",
        "details": {"medication": "etanercept", "dose": "50 mg", "frequency": "weekly", "action": "start", "reason": "treat_to_target_remission"},
    },
    {
        "ts": "2022-11-15T09:00:00Z",
        "kind": "visit",
        "summary": "Excellent response - approaching remission",
        "details": {"das28": 2.8, "swollen_joints": 1, "tender_joints": 2, "morning_stiffness_min": 15},
    },
    {
        "ts": "2022-11-15T10:00:00Z",
        "kind": "lab",
        "summary": "Labs normalizing",
        "details": {"CRP": 4.0, "ESR": 15, "RF": 55, "anti_CCP": 72},
    },
    {
        "ts": "2023-02-01T09:00:00Z",
        "kind": "visit",
        "summary": "Remission achieved",
        "details": {"das28": 2.4, "swollen_joints": 0, "tender_joints": 1, "morning_stiffness_min": 10},
    },
    {
        "ts": "2023-02-01T21:00:00Z",
        "kind": "journal",
        "summary": "So happy to be in remission",
        "details": {"mood": "elated", "pain_level": 1, "text": "Doctor said I'm in remission! Can't believe how different I feel from 8 months ago. So grateful we caught this early."},
    },
    {
        "ts": "2023-05-01T09:00:00Z",
        "kind": "visit",
        "summary": "Sustained remission - consider dose reduction",
        "details": {"das28": 2.2, "swollen_joints": 0, "tender_joints": 0, "morning_stiffness_min": 5},
    },
    {
        "ts": "2023-05-01T10:00:00Z",
        "kind": "med_change",
        "summary": "Reduce MTX to 12.5 mg weekly",
        "details": {"medication": "methotrexate", "dose": "12.5 mg", "frequency": "weekly", "action": "dose_reduction", "reason": "sustained_remission"},
    },
    {
        "ts": "2023-08-01T09:00:00Z",
        "kind": "visit",
        "summary": "Remission maintained on lower MTX dose",
        "details": {"das28": 2.3, "swollen_joints": 0, "tender_joints": 1, "morning_stiffness_min": 10},
    },
    {
        "ts": "2023-08-01T10:00:00Z",
        "kind": "lab",
        "summary": "Labs stable and normal",
        "details": {"CRP": 2.0, "ESR": 10, "RF": 50, "anti_CCP": 70},
    },
    {
        "ts": "2023-11-01T09:00:00Z",
        "kind": "visit",
        "summary": "Routine follow-up - continued remission",
        "details": {"das28": 2.1, "swollen_joints": 0, "tender_joints": 0, "morning_stiffness_min": 5},
    },
    {
        "ts": "2023-12-15T20:00:00Z",
        "kind": "journal",
        "summary": "Holiday season going well",
        "details": {"mood": "happy", "pain_level": 0, "text": "Feeling great through the holidays. Can do all my baking and crafts without any joint issues. What a difference from last year!"},
    },
    {
        "ts": "2024-02-01T09:00:00Z",
        "kind": "visit",
        "summary": "Annual comprehensive visit - stable remission",
        "details": {"das28": 2.0, "swollen_joints": 0, "tender_joints": 0, "morning_stiffness_min": 5},
    },
    {
        "ts": "2024-02-01T10:00:00Z",
        "kind": "lab",
        "summary": "Annual labs - all normal",
        "details": {"CRP": 1.5, "ESR": 8, "RF": 48, "anti_CCP": 68, "LFTs": "normal", "CBC": "normal"},
    },
    {
        "ts": "2024-05-01T09:00:00Z",
        "kind": "visit",
        "summary": "Routine visit - 2 years in remission",
        "details": {"das28": 2.4, "swollen_joints": 0, "tender_joints": 1, "morning_stiffness_min": 10},
    },
    {
        "ts": "2024-06-20T21:00:00Z",
        "kind": "journal",
        "summary": "Two years since diagnosis",
        "details": {"mood": "reflective", "pain_level": 1, "text": "Hard to believe it's been 2 years since my RA diagnosis. Feel so lucky that treatment worked so well. Barely think about it most days."},
    },
    {
        "ts": "2024-08-01T09:00:00Z",
        "kind": "visit",
        "summary": "Routine visit - stable",
        "details": {"das28": 2.3, "swollen_joints": 0, "tender_joints": 0, "morning_stiffness_min": 5},
    },
    {
        "ts": "2024-08-01T10:00:00Z",
        "kind": "lab",
        "summary": "Labs continue normal",
        "details": {"CRP": 1.8, "ESR": 10, "RF": 50, "anti_CCP": 70},
    },
    {
        "ts": "2024-11-01T09:00:00Z",
        "kind": "visit",
        "summary": "Routine visit - sustained remission",
        "details": {"das28": 2.1, "swollen_joints": 0, "tender_joints": 0, "morning_stiffness_min": 5},
    },
    {
        "ts": "2025-02-01T09:00:00Z",
        "kind": "visit",
        "summary": "Routine visit - nearly 3 years in remission",
        "details": {"das28": 2.2, "swollen_joints": 0, "tender_joints": 1, "morning_stiffness_min": 10},
    },
    {
        "ts": "2025-02-01T10:00:00Z",
        "kind": "lab",
        "summary": "Labs stable",
        "details": {"CRP": 1.8, "ESR": 12, "RF": 50, "anti_CCP": 70},
    },
    {
        "ts": "2025-03-15T20:00:00Z",
        "kind": "journal",
        "summary": "Feeling grateful",
        "details": {"mood": "content", "pain_level": 0, "text": "Another good day. Sometimes I forget I even have RA. Just a little achiness when it rains, nothing major."},
    },
    {
        "ts": "2025-05-01T09:00:00Z",
        "kind": "visit",
        "summary": "Routine visit - continued remission",
        "details": {"das28": 2.0, "swollen_joints": 0, "tender_joints": 0, "morning_stiffness_min": 5},
    },
    {
        "ts": "2025-05-01T10:00:00Z",
        "kind": "lab",
        "summary": "Labs excellent",
        "details": {"CRP": 1.5, "ESR": 10, "RF": 48, "anti_CCP": 68},
    },
    {
        "ts": "2025-08-01T09:00:00Z",
        "kind": "visit",
        "summary": "Routine visit - deep sustained remission",
        "details": {"das28": 1.8, "swollen_joints": 0, "tender_joints": 0, "morning_stiffness_min": 0},
    },
    {
        "ts": "2025-08-01T10:00:00Z",
        "kind": "lab",
        "summary": "Labs at best levels",
        "details": {"CRP": 1.2, "ESR": 8, "RF": 45, "anti_CCP": 65, "LFTs": "normal"},
    },
    {
        "ts": "2025-08-15T21:00:00Z",
        "kind": "journal",
        "summary": "Life feels normal",
        "details": {"mood": "happy", "pain_level": 0, "text": "Went hiking this weekend with no issues. RA feels like a distant memory most days. So thankful for modern medicine."},
    },
]


# ---------------------------------------------------------------------------
# Patient 3: Smoldering / high-risk
# 35F, seropositive RA, incomplete control on csDMARD, biologic recently started
# Multiple flares in last 12 months, DAS28 still moderate-high
# Frequent lab elevations, missed doses, high work stress
# ---------------------------------------------------------------------------

P3_PATIENT: DemoPatient = {
    "id": "P3",
    "label": "P3 - Smoldering / high risk",
    "summary": "35F with seropositive RA, incomplete control despite MTX, recently started tofacitinib, 4 flares in past 12 months",
    "diagnosis": "Seropositive rheumatoid arthritis (RF+, anti-CCP+) - moderate-high activity",
    "age": 35,
    "sex": "F",
    "serostatus": "seropositive",
    "meds": [
        {"name": "methotrexate", "dose": "20 mg", "frequency": "weekly", "start_date": "2024-02-01", "status": "ongoing"},
        {"name": "folic_acid", "dose": "1 mg", "frequency": "daily", "start_date": "2024-02-01", "status": "ongoing"},
        {"name": "tofacitinib", "dose": "5 mg", "frequency": "twice daily", "start_date": "2025-06-01", "status": "ongoing"},
    ],
    "recent_labs": [
        {"date": "2025-08-15", "CRP": 18.0, "ESR": 38, "RF": 125, "anti_CCP": 180},
        {"date": "2025-06-01", "CRP": 32.0, "ESR": 55, "RF": 135, "anti_CCP": 195},
        {"date": "2025-03-15", "CRP": 25.0, "ESR": 48, "RF": 130, "anti_CCP": 188},
    ],
    "das28_history": [
        {"date": "2025-08-15", "das28": 4.2, "category": "moderate_activity"},
        {"date": "2025-06-01", "das28": 5.4, "category": "high_activity"},
        {"date": "2025-03-15", "das28": 4.8, "category": "moderate_activity"},
        {"date": "2024-12-01", "das28": 5.2, "category": "high_activity"},
        {"date": "2024-09-01", "das28": 4.6, "category": "moderate_activity"},
    ],
    "recent_flares": [
        {"date": "2025-05-20", "severity": "moderate", "joints": ["wrists", "MCPs", "shoulders"], "duration_days": 14},
        {"date": "2025-02-10", "severity": "severe", "joints": ["knees", "ankles", "PIPs"], "duration_days": 18},
        {"date": "2024-11-15", "severity": "moderate", "joints": ["MCPs", "wrists"], "duration_days": 12},
        {"date": "2024-08-20", "severity": "moderate", "joints": ["shoulders", "elbows"], "duration_days": 10},
    ],
    "journal_highlights": [
        "Work stress is constant - can't take time off",
        "Sometimes forget MTX dose when traveling for work",
        "Hands hurt most mornings, takes 1-2 hours to loosen up",
        "Worried about joint damage",
        "Sleep is poor due to pain and stress",
    ],
}

P3_TIMELINE: List[DemoEvent] = [
    {
        "ts": "2024-02-01T09:00:00Z",
        "kind": "visit",
        "summary": "Initial rheumatology visit - moderate-high RA",
        "details": {"das28": 5.6, "swollen_joints": 10, "tender_joints": 16, "morning_stiffness_min": 120, "RF_positive": True, "anti_CCP_positive": True},
    },
    {
        "ts": "2024-02-01T10:00:00Z",
        "kind": "med_change",
        "summary": "Start methotrexate 15 mg weekly",
        "details": {"medication": "methotrexate", "dose": "15 mg", "frequency": "weekly", "action": "start"},
    },
    {
        "ts": "2024-02-01T11:00:00Z",
        "kind": "lab",
        "summary": "Baseline labs - significantly elevated",
        "details": {"CRP": 45.0, "ESR": 72, "RF": 140, "anti_CCP": 200},
    },
    {
        "ts": "2024-03-15T21:00:00Z",
        "kind": "journal",
        "summary": "Struggling with new diagnosis and work",
        "details": {"mood": "stressed", "pain_level": 7, "text": "Just diagnosed with RA and work is crazy busy. Can't take time off. Hands hurt so much by end of day."},
    },
    {
        "ts": "2024-04-15T09:00:00Z",
        "kind": "visit",
        "summary": "Partial response - increase MTX",
        "details": {"das28": 5.0, "swollen_joints": 8, "tender_joints": 12, "morning_stiffness_min": 90},
    },
    {
        "ts": "2024-04-15T10:00:00Z",
        "kind": "med_change",
        "summary": "Increase MTX to 20 mg weekly",
        "details": {"medication": "methotrexate", "dose": "20 mg", "frequency": "weekly", "action": "dose_increase"},
    },
    {
        "ts": "2024-06-01T09:00:00Z",
        "kind": "visit",
        "summary": "Still moderate activity despite MTX increase",
        "details": {"das28": 4.6, "swollen_joints": 6, "tender_joints": 10, "morning_stiffness_min": 75},
    },
    {
        "ts": "2024-06-01T10:00:00Z",
        "kind": "lab",
        "summary": "Labs still elevated",
        "details": {"CRP": 28.0, "ESR": 52, "RF": 135, "anti_CCP": 190},
    },
    {
        "ts": "2024-07-20T22:00:00Z",
        "kind": "journal",
        "summary": "Missed MTX dose while traveling",
        "details": {"mood": "frustrated", "pain_level": 6, "text": "Was on a work trip and forgot to pack my MTX. Missed this week's dose. Feeling guilty about it."},
    },
    {
        "ts": "2024-08-20T07:00:00Z",
        "kind": "flare",
        "summary": "Moderate flare - shoulders and elbows",
        "details": {"severity": "moderate", "joints": ["shoulders", "elbows"], "morning_stiffness_min": 150, "trigger": "missed_dose_stress"},
    },
    {
        "ts": "2024-08-20T14:00:00Z",
        "kind": "med_change",
        "summary": "Prednisone burst for flare",
        "details": {"medication": "prednisone", "dose": "30 mg", "frequency": "daily", "duration": "10 days taper", "action": "start"},
    },
    {
        "ts": "2024-09-01T09:00:00Z",
        "kind": "visit",
        "summary": "Post-flare visit - discuss biologic",
        "details": {"das28": 4.6, "swollen_joints": 5, "tender_joints": 9, "morning_stiffness_min": 80},
    },
    {
        "ts": "2024-09-01T21:00:00Z",
        "kind": "journal",
        "summary": "Doctor wants to add biologic",
        "details": {"mood": "anxious", "pain_level": 5, "text": "Doctor says I need a biologic but I'm scared of the side effects. Also worried about cost. Need to think about it."},
    },
    {
        "ts": "2024-10-15T09:00:00Z",
        "kind": "visit",
        "summary": "Follow-up - patient declined biologic for now",
        "details": {"das28": 4.8, "swollen_joints": 6, "tender_joints": 10, "morning_stiffness_min": 90},
    },
    {
        "ts": "2024-11-15T08:00:00Z",
        "kind": "flare",
        "summary": "Moderate flare - MCPs and wrists",
        "details": {"severity": "moderate", "joints": ["MCPs", "wrists"], "morning_stiffness_min": 120, "trigger": "work_deadline"},
    },
    {
        "ts": "2024-11-15T15:00:00Z",
        "kind": "med_change",
        "summary": "Another prednisone burst",
        "details": {"medication": "prednisone", "dose": "25 mg", "frequency": "daily", "duration": "7 days taper", "action": "start"},
    },
    {
        "ts": "2024-11-15T16:00:00Z",
        "kind": "lab",
        "summary": "Labs during flare",
        "details": {"CRP": 38.0, "ESR": 62, "RF": 138, "anti_CCP": 195},
    },
    {
        "ts": "2024-12-01T09:00:00Z",
        "kind": "visit",
        "summary": "Urgent discussion about disease control",
        "details": {"das28": 5.2, "swollen_joints": 8, "tender_joints": 12, "morning_stiffness_min": 100},
    },
    {
        "ts": "2024-12-15T20:00:00Z",
        "kind": "journal",
        "summary": "Feeling defeated",
        "details": {"mood": "depressed", "pain_level": 7, "text": "Another flare. Feel like I can't get this under control. Work is suffering. Everything hurts."},
    },
    {
        "ts": "2025-01-15T09:00:00Z",
        "kind": "visit",
        "summary": "Strongly recommend adding targeted therapy",
        "details": {"das28": 4.9, "swollen_joints": 7, "tender_joints": 11, "morning_stiffness_min": 90},
    },
    {
        "ts": "2025-02-10T07:00:00Z",
        "kind": "flare",
        "summary": "Severe flare - multiple joints",
        "details": {"severity": "severe", "joints": ["knees", "ankles", "PIPs"], "morning_stiffness_min": 180, "trigger": "viral_illness_stress"},
    },
    {
        "ts": "2025-02-10T14:00:00Z",
        "kind": "med_change",
        "summary": "Higher dose prednisone for severe flare",
        "details": {"medication": "prednisone", "dose": "40 mg", "frequency": "daily", "duration": "14 days taper", "action": "start"},
    },
    {
        "ts": "2025-02-10T15:00:00Z",
        "kind": "lab",
        "summary": "Labs very elevated during severe flare",
        "details": {"CRP": 52.0, "ESR": 78, "RF": 145, "anti_CCP": 205},
    },
    {
        "ts": "2025-03-01T21:00:00Z",
        "kind": "journal",
        "summary": "Worst flare yet",
        "details": {"mood": "scared", "pain_level": 9, "text": "This was the worst flare I've had. Could barely walk. Finally agreed to try the JAK inhibitor. Can't keep going like this."},
    },
    {
        "ts": "2025-03-15T09:00:00Z",
        "kind": "visit",
        "summary": "Post-severe flare - agree to start tofacitinib",
        "details": {"das28": 4.8, "swollen_joints": 6, "tender_joints": 10, "morning_stiffness_min": 85},
    },
    {
        "ts": "2025-03-15T10:00:00Z",
        "kind": "lab",
        "summary": "Pre-tofacitinib labs",
        "details": {"CRP": 25.0, "ESR": 48, "RF": 130, "anti_CCP": 188, "lipids": "normal", "CBC": "normal"},
    },
    {
        "ts": "2025-05-20T07:00:00Z",
        "kind": "flare",
        "summary": "Moderate flare while waiting for tofacitinib approval",
        "details": {"severity": "moderate", "joints": ["wrists", "MCPs", "shoulders"], "morning_stiffness_min": 120, "trigger": "insurance_delay_stress"},
    },
    {
        "ts": "2025-05-20T14:00:00Z",
        "kind": "med_change",
        "summary": "Prednisone burst while awaiting tofacitinib",
        "details": {"medication": "prednisone", "dose": "20 mg", "frequency": "daily", "duration": "7 days taper", "action": "start"},
    },
    {
        "ts": "2025-06-01T09:00:00Z",
        "kind": "visit",
        "summary": "Start tofacitinib - finally approved",
        "details": {"das28": 5.4, "swollen_joints": 8, "tender_joints": 14, "morning_stiffness_min": 110},
    },
    {
        "ts": "2025-06-01T10:00:00Z",
        "kind": "med_change",
        "summary": "Start tofacitinib 5 mg twice daily",
        "details": {"medication": "tofacitinib", "dose": "5 mg", "frequency": "twice daily", "action": "start"},
    },
    {
        "ts": "2025-06-01T11:00:00Z",
        "kind": "lab",
        "summary": "Baseline labs before tofacitinib",
        "details": {"CRP": 32.0, "ESR": 55, "RF": 135, "anti_CCP": 195},
    },
    {
        "ts": "2025-06-15T20:00:00Z",
        "kind": "journal",
        "summary": "Starting to feel a bit better",
        "details": {"mood": "cautiously hopeful", "pain_level": 5, "text": "Two weeks on tofacitinib. Maybe feeling a little better? Morning stiffness seems shorter. Trying not to get my hopes up."},
    },
    {
        "ts": "2025-07-15T09:00:00Z",
        "kind": "visit",
        "summary": "6-week tofacitinib check - some improvement",
        "details": {"das28": 4.5, "swollen_joints": 5, "tender_joints": 9, "morning_stiffness_min": 70},
    },
    {
        "ts": "2025-08-15T09:00:00Z",
        "kind": "visit",
        "summary": "10-week check - continued improvement but still moderate",
        "details": {"das28": 4.2, "swollen_joints": 4, "tender_joints": 7, "morning_stiffness_min": 60},
    },
    {
        "ts": "2025-08-15T10:00:00Z",
        "kind": "lab",
        "summary": "Labs improving on tofacitinib",
        "details": {"CRP": 18.0, "ESR": 38, "RF": 125, "anti_CCP": 180, "lipids": "slightly elevated", "CBC": "normal"},
    },
    {
        "ts": "2025-08-20T21:00:00Z",
        "kind": "journal",
        "summary": "Better but still struggling",
        "details": {"mood": "mixed", "pain_level": 4, "text": "Definitely better than before tofacitinib but still not great. Morning stiffness about an hour. Work stress hasn't let up. Trying to be more consistent with meds."},
    },
]


# ---------------------------------------------------------------------------
# Patient 4: Subjective heavy / psychosomatic noise
# 30F, RA with moderate objective disease activity but frequent subjective bad days
# Few true flares but many symptom reports
# Journal shows many bad days not matched by DAS28/labs
# ---------------------------------------------------------------------------

P4_PATIENT: DemoPatient = {
    "id": "P4",
    "label": "P4 - Subjective heavy / psychosomatic noise",
    "summary": "30F with RA, moderate objective activity but high subjective symptom burden, anxiety/depression comorbidity",
    "diagnosis": "Seropositive rheumatoid arthritis (RF+, anti-CCP+) with fibromyalgia features",
    "age": 30,
    "sex": "F",
    "serostatus": "seropositive",
    "meds": [
        {"name": "methotrexate", "dose": "15 mg", "frequency": "weekly", "start_date": "2024-03-01", "status": "ongoing"},
        {"name": "folic_acid", "dose": "1 mg", "frequency": "daily", "start_date": "2024-03-01", "status": "ongoing"},
        {"name": "hydroxychloroquine", "dose": "200 mg", "frequency": "twice daily", "start_date": "2024-06-01", "status": "ongoing"},
        {"name": "duloxetine", "dose": "60 mg", "frequency": "daily", "start_date": "2025-01-15", "status": "ongoing"},
    ],
    "recent_labs": [
        {"date": "2025-08-01", "CRP": 8.0, "ESR": 22, "RF": 65, "anti_CCP": 85},
        {"date": "2025-05-01", "CRP": 10.0, "ESR": 25, "RF": 68, "anti_CCP": 88},
        {"date": "2025-02-01", "CRP": 12.0, "ESR": 28, "RF": 70, "anti_CCP": 90},
    ],
    "das28_history": [
        {"date": "2025-08-01", "das28": 3.4, "category": "moderate_activity"},
        {"date": "2025-05-01", "das28": 3.6, "category": "moderate_activity"},
        {"date": "2025-02-01", "das28": 3.8, "category": "moderate_activity"},
        {"date": "2024-11-01", "das28": 3.5, "category": "moderate_activity"},
        {"date": "2024-08-01", "das28": 4.0, "category": "moderate_activity"},
    ],
    "recent_flares": [
        {"date": "2024-10-05", "severity": "mild", "joints": ["wrists"], "duration_days": 5},
    ],
    "journal_highlights": [
        "Everything hurts today, can barely move",
        "Terrible day, pain everywhere",
        "Exhausted and achy, must be a flare",
        "Good day for once, only mild stiffness",
        "Anxiety making everything worse",
        "Can't tell if it's RA or just stress",
    ],
}

P4_TIMELINE: List[DemoEvent] = [
    {
        "ts": "2024-03-01T09:00:00Z",
        "kind": "visit",
        "summary": "Initial diagnosis - moderate RA",
        "details": {"das28": 4.2, "swollen_joints": 5, "tender_joints": 12, "morning_stiffness_min": 60, "RF_positive": True, "anti_CCP_positive": True, "note": "High tender joint count relative to swollen"},
    },
    {
        "ts": "2024-03-01T10:00:00Z",
        "kind": "med_change",
        "summary": "Start methotrexate 15 mg weekly",
        "details": {"medication": "methotrexate", "dose": "15 mg", "frequency": "weekly", "action": "start"},
    },
    {
        "ts": "2024-03-01T11:00:00Z",
        "kind": "lab",
        "summary": "Baseline labs - moderately elevated",
        "details": {"CRP": 18.0, "ESR": 35, "RF": 75, "anti_CCP": 95},
    },
    {
        "ts": "2024-03-15T21:00:00Z",
        "kind": "journal",
        "summary": "Terrible day, everything hurts",
        "details": {"mood": "distressed", "pain_level": 9, "text": "Worst day ever. Every joint hurts. Can barely type. Must be having a major flare. Called in sick to work."},
    },
    {
        "ts": "2024-03-20T09:00:00Z",
        "kind": "visit",
        "summary": "Urgent visit for reported severe symptoms",
        "details": {"das28": 4.0, "swollen_joints": 4, "tender_joints": 10, "morning_stiffness_min": 45, "note": "Objective findings don't match reported severity"},
    },
    {
        "ts": "2024-04-10T20:00:00Z",
        "kind": "journal",
        "summary": "Another bad day",
        "details": {"mood": "frustrated", "pain_level": 8, "text": "Pain is unbearable. Took extra Tylenol. Why isn't the MTX working? Feel like I'm falling apart."},
    },
    {
        "ts": "2024-05-01T09:00:00Z",
        "kind": "visit",
        "summary": "Follow-up - objective improvement but patient reports no change",
        "details": {"das28": 3.8, "swollen_joints": 3, "tender_joints": 9, "morning_stiffness_min": 40},
    },
    {
        "ts": "2024-05-01T10:00:00Z",
        "kind": "lab",
        "summary": "Labs improving",
        "details": {"CRP": 14.0, "ESR": 30, "RF": 72, "anti_CCP": 92},
    },
    {
        "ts": "2024-05-15T22:00:00Z",
        "kind": "journal",
        "summary": "Exhausted and achy",
        "details": {"mood": "exhausted", "pain_level": 7, "text": "So tired. Whole body aches. Is this RA or am I just getting sick? Can't tell anymore. Everything blurs together."},
    },
    {
        "ts": "2024-06-01T09:00:00Z",
        "kind": "visit",
        "summary": "Add hydroxychloroquine for persistent symptoms",
        "details": {"das28": 4.0, "swollen_joints": 4, "tender_joints": 10, "morning_stiffness_min": 50},
    },
    {
        "ts": "2024-06-01T10:00:00Z",
        "kind": "med_change",
        "summary": "Add hydroxychloroquine 200 mg twice daily",
        "details": {"medication": "hydroxychloroquine", "dose": "200 mg", "frequency": "twice daily", "action": "start"},
    },
    {
        "ts": "2024-06-20T21:00:00Z",
        "kind": "journal",
        "summary": "Good day for once",
        "details": {"mood": "surprised", "pain_level": 3, "text": "Actually had a decent day today. Only mild stiffness in the morning. Maybe the new med is helping?"},
    },
    {
        "ts": "2024-07-15T20:00:00Z",
        "kind": "journal",
        "summary": "Back to feeling terrible",
        "details": {"mood": "hopeless", "pain_level": 8, "text": "Spoke too soon. Back to feeling awful. Pain everywhere. Can't sleep. Starting to think I'll never feel normal again."},
    },
    {
        "ts": "2024-08-01T09:00:00Z",
        "kind": "visit",
        "summary": "Stable objective disease but high symptom burden",
        "details": {"das28": 4.0, "swollen_joints": 4, "tender_joints": 11, "morning_stiffness_min": 45, "note": "Discussed fibromyalgia overlap, anxiety screening positive"},
    },
    {
        "ts": "2024-08-01T10:00:00Z",
        "kind": "lab",
        "summary": "Labs stable",
        "details": {"CRP": 12.0, "ESR": 28, "RF": 70, "anti_CCP": 90},
    },
    {
        "ts": "2024-09-10T21:00:00Z",
        "kind": "journal",
        "summary": "Anxiety making everything worse",
        "details": {"mood": "anxious", "pain_level": 7, "text": "Can't stop worrying about my RA getting worse. Every little ache makes me panic. Is this a flare starting? The anxiety is exhausting."},
    },
    {
        "ts": "2024-10-05T08:00:00Z",
        "kind": "flare",
        "summary": "Mild flare - wrists only",
        "details": {"severity": "mild", "joints": ["wrists"], "morning_stiffness_min": 75, "note": "First documented flare since diagnosis"},
    },
    {
        "ts": "2024-10-05T21:00:00Z",
        "kind": "journal",
        "summary": "Finally a real flare",
        "details": {"mood": "validated", "pain_level": 6, "text": "Doctor confirmed this is actually a flare. Wrists are swollen. At least I know I'm not imagining things. But also scared."},
    },
    {
        "ts": "2024-10-15T09:00:00Z",
        "kind": "visit",
        "summary": "Flare resolved, discuss central sensitization",
        "details": {"das28": 3.6, "swollen_joints": 2, "tender_joints": 8, "morning_stiffness_min": 35, "note": "Discussed fibromyalgia, central sensitization, referred to psychiatry"},
    },
    {
        "ts": "2024-11-01T09:00:00Z",
        "kind": "visit",
        "summary": "Routine visit - stable moderate activity",
        "details": {"das28": 3.5, "swollen_joints": 2, "tender_joints": 8, "morning_stiffness_min": 30},
    },
    {
        "ts": "2024-11-20T20:00:00Z",
        "kind": "journal",
        "summary": "Terrible day, pain everywhere",
        "details": {"mood": "distressed", "pain_level": 9, "text": "Everything hurts. Shoulders, back, hips, knees. Even my skin hurts. This can't all be RA. What's wrong with me?"},
    },
    {
        "ts": "2024-12-15T21:00:00Z",
        "kind": "journal",
        "summary": "Holiday stress making things worse",
        "details": {"mood": "overwhelmed", "pain_level": 7, "text": "Holiday stress is killing me. Pain is worse. Can't tell if it's RA or just tension. Dreading family gatherings."},
    },
    {
        "ts": "2025-01-15T09:00:00Z",
        "kind": "visit",
        "summary": "Start duloxetine for pain and mood",
        "details": {"das28": 3.8, "swollen_joints": 3, "tender_joints": 10, "morning_stiffness_min": 40, "note": "Starting duloxetine for fibromyalgia features and anxiety"},
    },
    {
        "ts": "2025-01-15T10:00:00Z",
        "kind": "med_change",
        "summary": "Start duloxetine 60 mg daily",
        "details": {"medication": "duloxetine", "dose": "60 mg", "frequency": "daily", "action": "start", "indication": "fibromyalgia_anxiety"},
    },
    {
        "ts": "2025-02-01T09:00:00Z",
        "kind": "visit",
        "summary": "Follow-up on duloxetine - some improvement in overall wellbeing",
        "details": {"das28": 3.8, "swollen_joints": 3, "tender_joints": 9, "morning_stiffness_min": 40},
    },
    {
        "ts": "2025-02-01T10:00:00Z",
        "kind": "lab",
        "summary": "Labs stable",
        "details": {"CRP": 12.0, "ESR": 28, "RF": 70, "anti_CCP": 90},
    },
    {
        "ts": "2025-02-20T21:00:00Z",
        "kind": "journal",
        "summary": "Duloxetine helping a bit",
        "details": {"mood": "slightly better", "pain_level": 5, "text": "The new antidepressant seems to be helping. Still have pain but I'm coping better. Sleep is a bit improved too."},
    },
    {
        "ts": "2025-03-15T20:00:00Z",
        "kind": "journal",
        "summary": "Bad day but trying to cope",
        "details": {"mood": "struggling", "pain_level": 7, "text": "Pain is bad today but trying to remember what therapist said about catastrophizing. It's hard. Everything still hurts."},
    },
    {
        "ts": "2025-04-10T21:00:00Z",
        "kind": "journal",
        "summary": "Can't tell if it's RA or stress",
        "details": {"mood": "confused", "pain_level": 6, "text": "Achy all over. Is this RA? Fibro? Just stress? I don't even know anymore. At least the anxiety is a bit better."},
    },
    {
        "ts": "2025-05-01T09:00:00Z",
        "kind": "visit",
        "summary": "Routine visit - objective disease stable",
        "details": {"das28": 3.6, "swollen_joints": 2, "tender_joints": 8, "morning_stiffness_min": 35, "note": "Patient reports variable symptoms, objective findings stable"},
    },
    {
        "ts": "2025-05-01T10:00:00Z",
        "kind": "lab",
        "summary": "Labs slightly improved",
        "details": {"CRP": 10.0, "ESR": 25, "RF": 68, "anti_CCP": 88},
    },
    {
        "ts": "2025-06-15T20:00:00Z",
        "kind": "journal",
        "summary": "Good week overall",
        "details": {"mood": "hopeful", "pain_level": 4, "text": "Had a pretty good week. Pain was manageable. Starting to accept that some days will be worse than others. Therapy is helping."},
    },
    {
        "ts": "2025-07-20T21:00:00Z",
        "kind": "journal",
        "summary": "Setback but trying to stay positive",
        "details": {"mood": "determined", "pain_level": 6, "text": "Rough few days but trying not to spiral. Pain is real but I know anxiety makes it worse. Taking it one day at a time."},
    },
    {
        "ts": "2025-08-01T09:00:00Z",
        "kind": "visit",
        "summary": "Routine visit - stable, patient coping better",
        "details": {"das28": 3.4, "swollen_joints": 2, "tender_joints": 7, "morning_stiffness_min": 30, "note": "Patient reports better coping despite ongoing symptoms"},
    },
    {
        "ts": "2025-08-01T10:00:00Z",
        "kind": "lab",
        "summary": "Labs at best levels",
        "details": {"CRP": 8.0, "ESR": 22, "RF": 65, "anti_CCP": 85},
    },
    {
        "ts": "2025-08-15T21:00:00Z",
        "kind": "journal",
        "summary": "Learning to live with uncertainty",
        "details": {"mood": "accepting", "pain_level": 5, "text": "Still have bad days but learning to accept them. RA is part of my life but doesn't have to define it. Therapy and duloxetine helping a lot."},
    },
]


# ---------------------------------------------------------------------------
# Aggregated registries
# ---------------------------------------------------------------------------

DEMO_PATIENTS: Dict[str, DemoPatient] = {
    "P1": P1_PATIENT,
    "P2": P2_PATIENT,
    "P3": P3_PATIENT,
    "P4": P4_PATIENT,
}

DEMO_TIMELINES: Dict[str, List[DemoEvent]] = {
    "P1": P1_TIMELINE,
    "P2": P2_TIMELINE,
    "P3": P3_TIMELINE,
    "P4": P4_TIMELINE,
}


def get_patient_list() -> List[Dict[str, str]]:
    """Return a list of {id, label, summary} for all demo patients."""
    return [
        {"id": p["id"], "label": p["label"], "summary": p["summary"]}
        for p in DEMO_PATIENTS.values()
    ]


def get_patient(patient_id: str) -> DemoPatient | None:
    """Return a single patient by ID, or None if not found."""
    return DEMO_PATIENTS.get(patient_id)


def get_timeline(patient_id: str, max_events: int = 200) -> List[DemoEvent]:
    """Return the timeline for a patient, capped at max_events."""
    timeline = DEMO_TIMELINES.get(patient_id, [])
    return timeline[:max_events]
