import uuid
from fastapi import APIRouter

router = APIRouter(prefix="/api/portal", tags=["portal"])


@router.post("/transcribe")
async def transcribe():
    return {
        "text": (
            "Patient reports increased joint stiffness in the morning, "
            "lasting approximately 90 minutes. Fatigue is rated 7 out of 10. "
            "No fever. Current medications: hydroxychloroquine 400mg daily, "
            "prednisone 5mg as needed."
        ),
        "duration_seconds": 47.3,
        "confidence": 0.91,
    }


@router.post("/encounter_note")
async def encounter_note(body: dict = None):
    return {
        "id": f"enc-{uuid.uuid4().hex[:8]}",
        "patient_id": "user-norman-dev",
        "provider": "Dr. Gregory House",
        "date": "2025-12-10",
        "chief_complaint": "Joint pain and fatigue",
        "subjective": (
            "Patient presents with worsening bilateral joint pain, "
            "morning stiffness >60 minutes, and fatigue rated 7/10. "
            "Symptoms have been progressively worsening over the past 2 weeks."
        ),
        "objective": {
            "vitals": {"bp": "118/76", "hr": 72, "temp": 98.4, "weight": "165 lbs"},
            "exam": "Mild synovitis noted bilateral MCPs. ROM preserved. No effusions.",
        },
        "assessment": (
            "Inflammatory arthropathy — possible SLE flare vs RA exacerbation. "
            "Band 3 instability per EoH framework."
        ),
        "plan": [
            "CRP, ESR, anti-dsDNA, CBC with differential",
            "Increase hydroxychloroquine monitoring",
            "Follow up in 2 weeks or sooner if symptoms worsen",
            "Patient educated on flare warning signs",
        ],
        "icd_codes": ["M32.9", "M06.9"],
    }


@router.post("/save-encounter")
async def save_encounter(body: dict = None):
    return {
        "saved": True,
        "id": f"enc-{uuid.uuid4().hex[:8]}",
        "status": "draft",
    }
