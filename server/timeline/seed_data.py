"""
Seed data for the EoH Timeline Engine.

This module provides example patient timeline data for testing and demonstration.
The data represents realistic autoimmune disease patterns without containing
any real patient information.

Usage:
    python -m server.timeline.seed_data --patient-id DEMO001

All data is synthetic and designed to demonstrate:
- Lab result patterns (CRP, ESR, RF, ANA, etc.)
- Symptom progression (joint pain, fatigue, morning stiffness)
- Medication history (DMARDs, biologics, NSAIDs)
- Flare events and their precursors
- Imaging findings
"""

import argparse
import asyncio
import json
import logging
import os
import sys
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from server.timeline.models import (
    EventType,
    EventSource,
    LabResult,
    SymptomData,
    MedicationData,
    FlareData,
    VisitData,
    ImagingData,
    TimelineEventCreate,
)

logger = logging.getLogger(__name__)


def generate_ra_like_patient(patient_id: str = "DEMO_RA_001") -> List[TimelineEventCreate]:
    """
    Generate a synthetic RA-like patient timeline.
    
    This patient demonstrates:
    - Symmetric small joint involvement
    - Positive RF and anti-CCP
    - Rising inflammatory markers before flares
    - Response to methotrexate
    - Morning stiffness patterns
    """
    events: List[TimelineEventCreate] = []
    base_date = datetime.now(timezone.utc) - timedelta(days=365)
    
    # Initial presentation - Day 0
    events.append(TimelineEventCreate(
        patient_id=patient_id,
        ts=base_date,
        event_type=EventType.VISIT,
        source=EventSource.EHR,
        structured=VisitData(
            visit_type="new_patient",
            provider="Dr. Smith",
            location="Rheumatology Clinic",
            chief_complaint="Joint pain and stiffness for 3 months",
            diagnoses=["Polyarthralgia, unspecified"],
        ).model_dump(),
        text="New patient visit for evaluation of joint pain. Patient reports 3 months of bilateral hand and wrist pain with morning stiffness lasting 2-3 hours. No prior rheumatologic history.",
        meta={"visit_number": 1},
    ))
    
    # Initial labs - Day 0
    events.extend([
        TimelineEventCreate(
            patient_id=patient_id,
            ts=base_date + timedelta(hours=2),
            event_type=EventType.LAB,
            source=EventSource.EHR,
            structured=LabResult(
                test_name="CRP",
                value=2.8,
                unit="mg/dL",
                reference_range="<0.5",
                flag="high",
            ).model_dump(),
            text="CRP elevated at 2.8 mg/dL (reference: <0.5 mg/dL), indicating active inflammation.",
            meta={"lab_panel": "inflammatory_markers"},
        ),
        TimelineEventCreate(
            patient_id=patient_id,
            ts=base_date + timedelta(hours=2),
            event_type=EventType.LAB,
            source=EventSource.EHR,
            structured=LabResult(
                test_name="ESR",
                value=45,
                unit="mm/hr",
                reference_range="0-20",
                flag="high",
            ).model_dump(),
            text="ESR elevated at 45 mm/hr (reference: 0-20 mm/hr).",
            meta={"lab_panel": "inflammatory_markers"},
        ),
        TimelineEventCreate(
            patient_id=patient_id,
            ts=base_date + timedelta(hours=2),
            event_type=EventType.LAB,
            source=EventSource.EHR,
            structured=LabResult(
                test_name="RF",
                value=85,
                unit="IU/mL",
                reference_range="<14",
                flag="high",
            ).model_dump(),
            text="Rheumatoid Factor positive at 85 IU/mL (reference: <14 IU/mL).",
            meta={"lab_panel": "autoimmune_panel"},
        ),
        TimelineEventCreate(
            patient_id=patient_id,
            ts=base_date + timedelta(hours=2),
            event_type=EventType.LAB,
            source=EventSource.EHR,
            structured=LabResult(
                test_name="Anti-CCP",
                value=120,
                unit="U/mL",
                reference_range="<20",
                flag="high",
            ).model_dump(),
            text="Anti-CCP antibodies strongly positive at 120 U/mL (reference: <20 U/mL).",
            meta={"lab_panel": "autoimmune_panel"},
        ),
        TimelineEventCreate(
            patient_id=patient_id,
            ts=base_date + timedelta(hours=2),
            event_type=EventType.LAB,
            source=EventSource.EHR,
            structured=LabResult(
                test_name="ANA",
                value=1,
                unit="titer",
                reference_range="<1:40",
                flag="normal",
                qualitative="negative",
            ).model_dump(),
            text="ANA negative.",
            meta={"lab_panel": "autoimmune_panel"},
        ),
    ])
    
    # Initial symptoms - Day 0
    events.append(TimelineEventCreate(
        patient_id=patient_id,
        ts=base_date + timedelta(hours=1),
        event_type=EventType.SYMPTOM,
        source=EventSource.CLINICIAN_NOTE,
        structured=SymptomData(
            symptom_name="joint_pain",
            severity=7,
            location="bilateral hands, wrists",
            duration="3 months",
            pattern="worse in morning",
            associated_symptoms=["morning stiffness", "swelling"],
        ).model_dump(),
        text="Bilateral hand and wrist pain, severity 7/10, with morning stiffness lasting 2-3 hours. Symmetric involvement of MCP and PIP joints.",
        meta={},
    ))
    
    # Hand X-rays - Day 7
    events.append(TimelineEventCreate(
        patient_id=patient_id,
        ts=base_date + timedelta(days=7),
        event_type=EventType.IMAGING,
        source=EventSource.EHR,
        structured=ImagingData(
            modality="X-ray",
            body_part="bilateral hands",
            findings="Periarticular osteopenia at MCP and PIP joints. No erosions identified. Soft tissue swelling at MCP 2-4 bilaterally.",
            impression="Findings consistent with early inflammatory arthritis. No erosive changes.",
            comparison="No prior imaging available.",
        ).model_dump(),
        text="Hand X-rays show periarticular osteopenia and soft tissue swelling at MCP joints bilaterally. No erosions. Findings consistent with early inflammatory arthritis.",
        meta={},
    ))
    
    # Start methotrexate - Day 14
    events.append(TimelineEventCreate(
        patient_id=patient_id,
        ts=base_date + timedelta(days=14),
        event_type=EventType.MEDICATION,
        source=EventSource.EHR,
        structured=MedicationData(
            medication_name="Methotrexate",
            dose="15mg",
            frequency="weekly",
            route="oral",
            status="started",
            indication="Rheumatoid arthritis",
        ).model_dump(),
        text="Started methotrexate 15mg weekly for treatment of rheumatoid arthritis. Folic acid 1mg daily also prescribed.",
        meta={"prescriber": "Dr. Smith"},
    ))
    
    # Follow-up symptoms improving - Day 60
    events.append(TimelineEventCreate(
        patient_id=patient_id,
        ts=base_date + timedelta(days=60),
        event_type=EventType.SYMPTOM,
        source=EventSource.PATIENT_UPLOAD,
        structured=SymptomData(
            symptom_name="joint_pain",
            severity=4,
            location="bilateral hands",
            duration="ongoing",
            pattern="improving",
            associated_symptoms=["morning stiffness 45 min"],
        ).model_dump(),
        text="Joint pain improving on methotrexate. Severity now 4/10. Morning stiffness reduced to 45 minutes.",
        meta={},
    ))
    
    # Labs improving - Day 60
    events.extend([
        TimelineEventCreate(
            patient_id=patient_id,
            ts=base_date + timedelta(days=60),
            event_type=EventType.LAB,
            source=EventSource.EHR,
            structured=LabResult(
                test_name="CRP",
                value=1.2,
                unit="mg/dL",
                reference_range="<0.5",
                flag="high",
            ).model_dump(),
            text="CRP improved to 1.2 mg/dL (was 2.8 mg/dL).",
            meta={"lab_panel": "inflammatory_markers"},
        ),
        TimelineEventCreate(
            patient_id=patient_id,
            ts=base_date + timedelta(days=60),
            event_type=EventType.LAB,
            source=EventSource.EHR,
            structured=LabResult(
                test_name="ESR",
                value=28,
                unit="mm/hr",
                reference_range="0-20",
                flag="high",
            ).model_dump(),
            text="ESR improved to 28 mm/hr (was 45 mm/hr).",
            meta={"lab_panel": "inflammatory_markers"},
        ),
    ])
    
    # Patient journal entry - Day 90
    events.append(TimelineEventCreate(
        patient_id=patient_id,
        ts=base_date + timedelta(days=90),
        event_type=EventType.JOURNAL,
        source=EventSource.JOURNAL,
        structured={
            "mood": "good",
            "energy_level": 7,
            "content": "Feeling much better on the methotrexate. Hands still a bit stiff in the morning but much improved from before.",
        },
        text="Patient journal: Feeling much better on methotrexate. Morning stiffness improved. Energy level 7/10.",
        meta={},
    ))
    
    # Flare precursor - Day 150 (missed doses)
    events.append(TimelineEventCreate(
        patient_id=patient_id,
        ts=base_date + timedelta(days=150),
        event_type=EventType.MED_CHANGE,
        source=EventSource.PATIENT_UPLOAD,
        structured={
            "medication_name": "Methotrexate",
            "change_type": "missed_doses",
            "reason": "GI upset",
            "duration": "2 weeks",
        },
        text="Patient reports missing methotrexate doses for 2 weeks due to GI upset.",
        meta={},
    ))
    
    # Flare precursor - Day 165 (rising markers)
    events.extend([
        TimelineEventCreate(
            patient_id=patient_id,
            ts=base_date + timedelta(days=165),
            event_type=EventType.LAB,
            source=EventSource.EHR,
            structured=LabResult(
                test_name="CRP",
                value=3.5,
                unit="mg/dL",
                reference_range="<0.5",
                flag="high",
            ).model_dump(),
            text="CRP rising to 3.5 mg/dL, indicating increasing inflammation.",
            meta={"lab_panel": "inflammatory_markers"},
        ),
        TimelineEventCreate(
            patient_id=patient_id,
            ts=base_date + timedelta(days=165),
            event_type=EventType.SYMPTOM,
            source=EventSource.PATIENT_UPLOAD,
            structured=SymptomData(
                symptom_name="fatigue",
                severity=6,
                duration="1 week",
                pattern="worsening",
            ).model_dump(),
            text="Increasing fatigue over the past week, severity 6/10.",
            meta={},
        ),
    ])
    
    # Flare event - Day 180
    events.append(TimelineEventCreate(
        patient_id=patient_id,
        ts=base_date + timedelta(days=180),
        event_type=EventType.FLARE,
        source=EventSource.CLINICIAN_NOTE,
        structured=FlareData(
            severity="moderate",
            duration_days=14,
            joints_involved=["bilateral MCPs", "bilateral PIPs", "bilateral wrists"],
            triggers=["medication gap"],
            treatment_response="prednisone taper",
        ).model_dump(),
        text="Moderate disease flare with bilateral hand and wrist involvement. Triggered by 2-week methotrexate gap. Started prednisone 20mg taper.",
        meta={},
    ))
    
    # Labs during flare - Day 180
    events.extend([
        TimelineEventCreate(
            patient_id=patient_id,
            ts=base_date + timedelta(days=180),
            event_type=EventType.LAB,
            source=EventSource.EHR,
            structured=LabResult(
                test_name="CRP",
                value=5.2,
                unit="mg/dL",
                reference_range="<0.5",
                flag="high",
            ).model_dump(),
            text="CRP elevated at 5.2 mg/dL during flare.",
            meta={"lab_panel": "inflammatory_markers"},
        ),
        TimelineEventCreate(
            patient_id=patient_id,
            ts=base_date + timedelta(days=180),
            event_type=EventType.LAB,
            source=EventSource.EHR,
            structured=LabResult(
                test_name="ESR",
                value=58,
                unit="mm/hr",
                reference_range="0-20",
                flag="high",
            ).model_dump(),
            text="ESR elevated at 58 mm/hr during flare.",
            meta={"lab_panel": "inflammatory_markers"},
        ),
    ])
    
    # Prednisone started - Day 180
    events.append(TimelineEventCreate(
        patient_id=patient_id,
        ts=base_date + timedelta(days=180),
        event_type=EventType.MEDICATION,
        source=EventSource.EHR,
        structured=MedicationData(
            medication_name="Prednisone",
            dose="20mg",
            frequency="daily, tapering",
            route="oral",
            status="started",
            indication="RA flare",
        ).model_dump(),
        text="Started prednisone 20mg daily with taper for RA flare management.",
        meta={},
    ))
    
    # Post-flare improvement - Day 210
    events.extend([
        TimelineEventCreate(
            patient_id=patient_id,
            ts=base_date + timedelta(days=210),
            event_type=EventType.LAB,
            source=EventSource.EHR,
            structured=LabResult(
                test_name="CRP",
                value=0.8,
                unit="mg/dL",
                reference_range="<0.5",
                flag="high",
            ).model_dump(),
            text="CRP improved to 0.8 mg/dL after flare treatment.",
            meta={"lab_panel": "inflammatory_markers"},
        ),
        TimelineEventCreate(
            patient_id=patient_id,
            ts=base_date + timedelta(days=210),
            event_type=EventType.SYMPTOM,
            source=EventSource.PATIENT_UPLOAD,
            structured=SymptomData(
                symptom_name="joint_pain",
                severity=3,
                location="bilateral hands",
                pattern="improving",
            ).model_dump(),
            text="Joint pain improving after flare treatment. Severity 3/10.",
            meta={},
        ),
    ])
    
    # Methotrexate dose increase - Day 210
    events.append(TimelineEventCreate(
        patient_id=patient_id,
        ts=base_date + timedelta(days=210),
        event_type=EventType.MED_CHANGE,
        source=EventSource.EHR,
        structured={
            "medication_name": "Methotrexate",
            "change_type": "dose_increase",
            "old_dose": "15mg weekly",
            "new_dose": "20mg weekly",
            "reason": "suboptimal disease control",
        },
        text="Methotrexate increased from 15mg to 20mg weekly due to recent flare.",
        meta={},
    ))
    
    # Recent labs - Day 330
    events.extend([
        TimelineEventCreate(
            patient_id=patient_id,
            ts=base_date + timedelta(days=330),
            event_type=EventType.LAB,
            source=EventSource.EHR,
            structured=LabResult(
                test_name="CRP",
                value=0.6,
                unit="mg/dL",
                reference_range="<0.5",
                flag="borderline",
            ).model_dump(),
            text="CRP near normal at 0.6 mg/dL.",
            meta={"lab_panel": "inflammatory_markers"},
        ),
        TimelineEventCreate(
            patient_id=patient_id,
            ts=base_date + timedelta(days=330),
            event_type=EventType.LAB,
            source=EventSource.EHR,
            structured=LabResult(
                test_name="ESR",
                value=18,
                unit="mm/hr",
                reference_range="0-20",
                flag="normal",
            ).model_dump(),
            text="ESR normalized at 18 mm/hr.",
            meta={"lab_panel": "inflammatory_markers"},
        ),
    ])
    
    # Recent visit - Day 350
    events.append(TimelineEventCreate(
        patient_id=patient_id,
        ts=base_date + timedelta(days=350),
        event_type=EventType.VISIT,
        source=EventSource.EHR,
        structured=VisitData(
            visit_type="follow_up",
            provider="Dr. Smith",
            location="Rheumatology Clinic",
            chief_complaint="Routine follow-up",
            diagnoses=["Rheumatoid arthritis, seropositive"],
        ).model_dump(),
        text="Routine follow-up visit. Disease well-controlled on methotrexate 20mg weekly. No active synovitis on exam. Plan to continue current regimen.",
        meta={"visit_number": 6},
    ))
    
    # Recent symptom report - Day 360
    events.append(TimelineEventCreate(
        patient_id=patient_id,
        ts=base_date + timedelta(days=360),
        event_type=EventType.SYMPTOM,
        source=EventSource.PATIENT_UPLOAD,
        structured=SymptomData(
            symptom_name="morning_stiffness",
            severity=2,
            duration="20 minutes",
            pattern="stable",
        ).model_dump(),
        text="Morning stiffness minimal, lasting about 20 minutes. Overall feeling well.",
        meta={},
    ))
    
    return events


def generate_lupus_like_patient(patient_id: str = "DEMO_SLE_001") -> List[TimelineEventCreate]:
    """
    Generate a synthetic lupus-like patient timeline.
    
    This patient demonstrates:
    - Positive ANA with specific antibodies
    - Multisystem involvement (skin, joints, kidneys)
    - Photosensitivity and malar rash
    - Complement consumption during flares
    """
    events: List[TimelineEventCreate] = []
    base_date = datetime.now(timezone.utc) - timedelta(days=300)
    
    # Initial presentation
    events.append(TimelineEventCreate(
        patient_id=patient_id,
        ts=base_date,
        event_type=EventType.VISIT,
        source=EventSource.EHR,
        structured=VisitData(
            visit_type="new_patient",
            provider="Dr. Johnson",
            location="Rheumatology Clinic",
            chief_complaint="Fatigue, joint pain, facial rash",
            diagnoses=["Systemic lupus erythematosus, suspected"],
        ).model_dump(),
        text="New patient presenting with 6 months of fatigue, arthralgias, and photosensitive facial rash. Reports hair loss and oral ulcers.",
        meta={},
    ))
    
    # Initial labs
    events.extend([
        TimelineEventCreate(
            patient_id=patient_id,
            ts=base_date + timedelta(hours=2),
            event_type=EventType.LAB,
            source=EventSource.EHR,
            structured=LabResult(
                test_name="ANA",
                value=1280,
                unit="titer",
                reference_range="<1:40",
                flag="high",
                qualitative="positive, homogeneous pattern",
            ).model_dump(),
            text="ANA strongly positive at 1:1280 with homogeneous pattern.",
            meta={"lab_panel": "autoimmune_panel"},
        ),
        TimelineEventCreate(
            patient_id=patient_id,
            ts=base_date + timedelta(hours=2),
            event_type=EventType.LAB,
            source=EventSource.EHR,
            structured=LabResult(
                test_name="Anti-dsDNA",
                value=85,
                unit="IU/mL",
                reference_range="<25",
                flag="high",
            ).model_dump(),
            text="Anti-dsDNA antibodies elevated at 85 IU/mL.",
            meta={"lab_panel": "autoimmune_panel"},
        ),
        TimelineEventCreate(
            patient_id=patient_id,
            ts=base_date + timedelta(hours=2),
            event_type=EventType.LAB,
            source=EventSource.EHR,
            structured=LabResult(
                test_name="C3",
                value=65,
                unit="mg/dL",
                reference_range="90-180",
                flag="low",
            ).model_dump(),
            text="C3 complement low at 65 mg/dL, suggesting consumption.",
            meta={"lab_panel": "complement"},
        ),
        TimelineEventCreate(
            patient_id=patient_id,
            ts=base_date + timedelta(hours=2),
            event_type=EventType.LAB,
            source=EventSource.EHR,
            structured=LabResult(
                test_name="C4",
                value=8,
                unit="mg/dL",
                reference_range="16-48",
                flag="low",
            ).model_dump(),
            text="C4 complement low at 8 mg/dL.",
            meta={"lab_panel": "complement"},
        ),
    ])
    
    # Symptoms
    events.append(TimelineEventCreate(
        patient_id=patient_id,
        ts=base_date + timedelta(hours=1),
        event_type=EventType.SYMPTOM,
        source=EventSource.CLINICIAN_NOTE,
        structured=SymptomData(
            symptom_name="malar_rash",
            severity=6,
            location="face, bilateral cheeks",
            duration="3 months",
            pattern="worse with sun exposure",
            associated_symptoms=["photosensitivity", "fatigue"],
        ).model_dump(),
        text="Malar rash present, butterfly distribution across cheeks sparing nasolabial folds. Worsens with sun exposure.",
        meta={},
    ))
    
    # Start hydroxychloroquine - Day 7
    events.append(TimelineEventCreate(
        patient_id=patient_id,
        ts=base_date + timedelta(days=7),
        event_type=EventType.MEDICATION,
        source=EventSource.EHR,
        structured=MedicationData(
            medication_name="Hydroxychloroquine",
            dose="400mg",
            frequency="daily",
            route="oral",
            status="started",
            indication="Systemic lupus erythematosus",
        ).model_dump(),
        text="Started hydroxychloroquine 400mg daily for SLE.",
        meta={},
    ))
    
    # Flare with renal involvement - Day 120
    events.extend([
        TimelineEventCreate(
            patient_id=patient_id,
            ts=base_date + timedelta(days=120),
            event_type=EventType.LAB,
            source=EventSource.EHR,
            structured=LabResult(
                test_name="Anti-dsDNA",
                value=180,
                unit="IU/mL",
                reference_range="<25",
                flag="high",
            ).model_dump(),
            text="Anti-dsDNA rising to 180 IU/mL, concerning for disease activity.",
            meta={},
        ),
        TimelineEventCreate(
            patient_id=patient_id,
            ts=base_date + timedelta(days=120),
            event_type=EventType.LAB,
            source=EventSource.EHR,
            structured=LabResult(
                test_name="Urine protein/creatinine ratio",
                value=1.2,
                unit="g/g",
                reference_range="<0.2",
                flag="high",
            ).model_dump(),
            text="Proteinuria detected, urine protein/creatinine ratio 1.2 g/g.",
            meta={},
        ),
        TimelineEventCreate(
            patient_id=patient_id,
            ts=base_date + timedelta(days=120),
            event_type=EventType.FLARE,
            source=EventSource.CLINICIAN_NOTE,
            structured=FlareData(
                severity="moderate-severe",
                duration_days=30,
                joints_involved=["bilateral hands", "bilateral knees"],
                triggers=["sun exposure", "stress"],
                treatment_response="prednisone + mycophenolate",
                organ_involvement=["kidneys", "skin", "joints"],
            ).model_dump(),
            text="Lupus flare with renal involvement. Proteinuria 1.2 g/g, rising anti-dsDNA. Started prednisone and mycophenolate.",
            meta={},
        ),
    ])
    
    # Recent stable labs - Day 280
    events.extend([
        TimelineEventCreate(
            patient_id=patient_id,
            ts=base_date + timedelta(days=280),
            event_type=EventType.LAB,
            source=EventSource.EHR,
            structured=LabResult(
                test_name="Anti-dsDNA",
                value=45,
                unit="IU/mL",
                reference_range="<25",
                flag="high",
            ).model_dump(),
            text="Anti-dsDNA improved to 45 IU/mL on treatment.",
            meta={},
        ),
        TimelineEventCreate(
            patient_id=patient_id,
            ts=base_date + timedelta(days=280),
            event_type=EventType.LAB,
            source=EventSource.EHR,
            structured=LabResult(
                test_name="C3",
                value=95,
                unit="mg/dL",
                reference_range="90-180",
                flag="normal",
            ).model_dump(),
            text="C3 complement normalized at 95 mg/dL.",
            meta={},
        ),
        TimelineEventCreate(
            patient_id=patient_id,
            ts=base_date + timedelta(days=280),
            event_type=EventType.LAB,
            source=EventSource.EHR,
            structured=LabResult(
                test_name="Urine protein/creatinine ratio",
                value=0.3,
                unit="g/g",
                reference_range="<0.2",
                flag="borderline",
            ).model_dump(),
            text="Proteinuria improved to 0.3 g/g.",
            meta={},
        ),
    ])
    
    return events


def generate_psa_like_patient(patient_id: str = "DEMO_PSA_001") -> List[TimelineEventCreate]:
    """
    Generate a synthetic psoriatic arthritis-like patient timeline.
    
    This patient demonstrates:
    - Psoriasis preceding arthritis
    - Asymmetric oligoarthritis
    - Enthesitis and dactylitis
    - Nail changes
    """
    events: List[TimelineEventCreate] = []
    base_date = datetime.now(timezone.utc) - timedelta(days=400)
    
    # Psoriasis history
    events.append(TimelineEventCreate(
        patient_id=patient_id,
        ts=base_date,
        event_type=EventType.NOTE,
        source=EventSource.EHR,
        structured={
            "note_type": "history",
            "content": "10-year history of plaque psoriasis affecting scalp, elbows, and knees.",
        },
        text="Patient has 10-year history of plaque psoriasis. Currently managed with topical steroids.",
        meta={},
    ))
    
    # New joint symptoms - Day 30
    events.append(TimelineEventCreate(
        patient_id=patient_id,
        ts=base_date + timedelta(days=30),
        event_type=EventType.SYMPTOM,
        source=EventSource.PATIENT_UPLOAD,
        structured=SymptomData(
            symptom_name="joint_pain",
            severity=6,
            location="right knee, left ankle",
            duration="2 weeks",
            pattern="asymmetric",
            associated_symptoms=["swelling", "stiffness"],
        ).model_dump(),
        text="New onset asymmetric joint pain affecting right knee and left ankle. Swelling noted.",
        meta={},
    ))
    
    # Dactylitis - Day 45
    events.append(TimelineEventCreate(
        patient_id=patient_id,
        ts=base_date + timedelta(days=45),
        event_type=EventType.SYMPTOM,
        source=EventSource.CLINICIAN_NOTE,
        structured=SymptomData(
            symptom_name="dactylitis",
            severity=7,
            location="right 3rd toe",
            duration="1 week",
            pattern="sausage digit",
        ).model_dump(),
        text="Dactylitis of right 3rd toe - classic sausage digit appearance.",
        meta={},
    ))
    
    # Labs - Day 50
    events.extend([
        TimelineEventCreate(
            patient_id=patient_id,
            ts=base_date + timedelta(days=50),
            event_type=EventType.LAB,
            source=EventSource.EHR,
            structured=LabResult(
                test_name="RF",
                value=8,
                unit="IU/mL",
                reference_range="<14",
                flag="normal",
            ).model_dump(),
            text="RF negative at 8 IU/mL.",
            meta={},
        ),
        TimelineEventCreate(
            patient_id=patient_id,
            ts=base_date + timedelta(days=50),
            event_type=EventType.LAB,
            source=EventSource.EHR,
            structured=LabResult(
                test_name="HLA-B27",
                value=1,
                unit="",
                reference_range="negative",
                flag="positive",
                qualitative="positive",
            ).model_dump(),
            text="HLA-B27 positive.",
            meta={},
        ),
        TimelineEventCreate(
            patient_id=patient_id,
            ts=base_date + timedelta(days=50),
            event_type=EventType.LAB,
            source=EventSource.EHR,
            structured=LabResult(
                test_name="CRP",
                value=1.8,
                unit="mg/dL",
                reference_range="<0.5",
                flag="high",
            ).model_dump(),
            text="CRP elevated at 1.8 mg/dL.",
            meta={},
        ),
    ])
    
    # Start NSAID - Day 55
    events.append(TimelineEventCreate(
        patient_id=patient_id,
        ts=base_date + timedelta(days=55),
        event_type=EventType.MEDICATION,
        source=EventSource.EHR,
        structured=MedicationData(
            medication_name="Naproxen",
            dose="500mg",
            frequency="twice daily",
            route="oral",
            status="started",
            indication="Psoriatic arthritis",
        ).model_dump(),
        text="Started naproxen 500mg BID for psoriatic arthritis.",
        meta={},
    ))
    
    # Enthesitis - Day 100
    events.append(TimelineEventCreate(
        patient_id=patient_id,
        ts=base_date + timedelta(days=100),
        event_type=EventType.SYMPTOM,
        source=EventSource.CLINICIAN_NOTE,
        structured=SymptomData(
            symptom_name="enthesitis",
            severity=5,
            location="bilateral Achilles tendons",
            duration="3 weeks",
            pattern="worse with activity",
        ).model_dump(),
        text="Bilateral Achilles enthesitis. Tenderness at tendon insertions.",
        meta={},
    ))
    
    # Start biologic - Day 120
    events.append(TimelineEventCreate(
        patient_id=patient_id,
        ts=base_date + timedelta(days=120),
        event_type=EventType.MEDICATION,
        source=EventSource.EHR,
        structured=MedicationData(
            medication_name="Adalimumab",
            dose="40mg",
            frequency="every 2 weeks",
            route="subcutaneous",
            status="started",
            indication="Psoriatic arthritis",
        ).model_dump(),
        text="Started adalimumab 40mg every 2 weeks for psoriatic arthritis with inadequate NSAID response.",
        meta={},
    ))
    
    # Good response - Day 200
    events.extend([
        TimelineEventCreate(
            patient_id=patient_id,
            ts=base_date + timedelta(days=200),
            event_type=EventType.LAB,
            source=EventSource.EHR,
            structured=LabResult(
                test_name="CRP",
                value=0.4,
                unit="mg/dL",
                reference_range="<0.5",
                flag="normal",
            ).model_dump(),
            text="CRP normalized at 0.4 mg/dL on adalimumab.",
            meta={},
        ),
        TimelineEventCreate(
            patient_id=patient_id,
            ts=base_date + timedelta(days=200),
            event_type=EventType.SYMPTOM,
            source=EventSource.PATIENT_UPLOAD,
            structured=SymptomData(
                symptom_name="joint_pain",
                severity=2,
                location="minimal",
                pattern="well controlled",
            ).model_dump(),
            text="Joint symptoms well controlled on adalimumab. Minimal pain, severity 2/10.",
            meta={},
        ),
    ])
    
    return events


async def seed_patient_data(patient_id: str, patient_type: str = "ra") -> int:
    """
    Seed patient timeline data into the database.
    
    Args:
        patient_id: Patient identifier
        patient_type: Type of patient data to generate ("ra", "sle", "psa")
    
    Returns:
        Number of events created
    """
    from server.timeline.engine import TimelineEngine
    from server.db.session import get_async_session
    
    # Generate events based on patient type
    if patient_type == "ra":
        events = generate_ra_like_patient(patient_id)
    elif patient_type == "sle":
        events = generate_lupus_like_patient(patient_id)
    elif patient_type == "psa":
        events = generate_psa_like_patient(patient_id)
    else:
        raise ValueError(f"Unknown patient type: {patient_type}")
    
    logger.info(f"Generated {len(events)} events for patient {patient_id} ({patient_type})")
    
    # Store events in database
    engine = TimelineEngine()
    
    async with get_async_session() as session:
        stored_events = await engine.store_events_batch(session, events)
        await session.commit()
        logger.info(f"Stored {len(stored_events)} events in database")
        return len(stored_events)


def main():
    """CLI entry point for seeding patient data."""
    parser = argparse.ArgumentParser(
        description="Seed example patient timeline data for the EoH Timeline Engine"
    )
    parser.add_argument(
        "--patient-id",
        type=str,
        default="DEMO001",
        help="Patient identifier (default: DEMO001)",
    )
    parser.add_argument(
        "--type",
        type=str,
        choices=["ra", "sle", "psa", "all"],
        default="ra",
        help="Type of patient data to generate (default: ra)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Generate events without storing to database",
    )
    parser.add_argument(
        "--output",
        type=str,
        help="Output JSON file for dry run (optional)",
    )
    
    args = parser.parse_args()
    
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    
    if args.type == "all":
        patient_types = ["ra", "sle", "psa"]
    else:
        patient_types = [args.type]
    
    all_events: List[Dict[str, Any]] = []
    
    for pt in patient_types:
        if args.type == "all":
            pid = f"{args.patient_id}_{pt.upper()}"
        else:
            pid = args.patient_id
        
        if pt == "ra":
            events = generate_ra_like_patient(pid)
        elif pt == "sle":
            events = generate_lupus_like_patient(pid)
        elif pt == "psa":
            events = generate_psa_like_patient(pid)
        else:
            continue
        
        logger.info(f"Generated {len(events)} events for patient {pid} ({pt})")
        
        if args.dry_run:
            for e in events:
                all_events.append({
                    "patient_id": e.patient_id,
                    "ts": e.ts.isoformat(),
                    "event_type": e.event_type.value,
                    "source": e.source.value,
                    "structured": e.structured,
                    "text": e.text,
                    "meta": e.meta,
                })
        else:
            count = asyncio.run(seed_patient_data(pid, pt))
            logger.info(f"Seeded {count} events for patient {pid}")
    
    if args.dry_run:
        if args.output:
            with open(args.output, "w") as f:
                json.dump(all_events, f, indent=2)
            logger.info(f"Wrote {len(all_events)} events to {args.output}")
        else:
            print(json.dumps(all_events, indent=2))


if __name__ == "__main__":
    main()
