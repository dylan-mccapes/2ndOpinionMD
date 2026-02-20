"""
Doctor portal ambient coding API (Phase 6a).
POST /api/portal/transcribe  - Accept audio chunk, return transcript via Whisper
POST /api/portal/extract     - Transcript text -> structured clinical extraction
POST /api/portal/encounter_note - Accepted codes + transcript -> encounter note
"""
import json
import logging
import os
import tempfile
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from server.api.auth_postgres import get_current_user_postgres
from server.db.session import get_session

logger = logging.getLogger(__name__)

router = APIRouter()


def _require_doctor(current_user: Any) -> Any:
    ut = getattr(current_user, "user_type", "patient")
    if ut != "doctor":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Doctor access required")
    return current_user


@router.post("/transcribe")
async def transcribe_audio(
    file: UploadFile = File(...),
    patient_id: Optional[str] = Form(None),
    chunk_index: Optional[int] = Form(None),
    current_user: Any = Depends(get_current_user_postgres),
) -> dict:
    """
    Accept an audio chunk (WAV/WebM), transcribe via Whisper, return text segment.
    Audio stays on-machine (HIPAA invariant).
    """
    _require_doctor(current_user)

    if not file.content_type or not (
        file.content_type.startswith("audio/") or file.content_type == "application/octet-stream"
    ):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Expected audio file, got {file.content_type}")

    audio_bytes = await file.read()
    if len(audio_bytes) == 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Empty audio file")
    if len(audio_bytes) > 25 * 1024 * 1024:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="Audio chunk too large (max 25MB)")

    suffix = ".wav"
    if file.content_type and "webm" in file.content_type:
        suffix = ".webm"
    elif file.content_type and "mp4" in file.content_type:
        suffix = ".mp4"
    elif file.content_type and "ogg" in file.content_type:
        suffix = ".ogg"

    transcript_text = ""
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp.write(audio_bytes)
            tmp_path = tmp.name

        try:
            import whisper
            model_name = os.getenv("WHISPER_MODEL", "base")
            model = whisper.load_model(model_name)
            result = model.transcribe(tmp_path, language="en", fp16=False)
            transcript_text = (result.get("text") or "").strip()
        except ImportError:
            logger.warning("Whisper not installed. Falling back to OpenAI Whisper API.")
            try:
                from openai import OpenAI
                client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
                with open(tmp_path, "rb") as af:
                    resp = client.audio.transcriptions.create(
                        model="whisper-1",
                        file=af,
                        language="en",
                    )
                transcript_text = (resp.text or "").strip()
            except Exception as e:
                logger.error("Whisper API fallback failed: %s", e)
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Transcription failed: {e}",
                )
        except Exception as e:
            logger.error("Local Whisper transcription failed: %s", e)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Transcription failed: {e}",
            )
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)

    return {
        "text": transcript_text,
        "chunk_index": chunk_index,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "patient_id": patient_id,
    }


class ExtractRequest(BaseModel):
    transcript: str
    patient_id: Optional[str] = None


@router.post("/extract")
async def extract_clinical(
    body: ExtractRequest,
    current_user: Any = Depends(get_current_user_postgres),
) -> dict:
    """
    Extract structured clinical information from transcript text.
    Returns: chief_complaint, symptoms, severity, onset, medications, prior_diagnoses,
             family_history, environmental_factors.
    """
    _require_doctor(current_user)

    transcript = (body.transcript or "").strip()
    if not transcript:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Empty transcript")

    try:
        from openai import OpenAI
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        model_used = os.getenv("CHAT_MODEL", "gpt-4o-mini")

        prompt = f"""You are a clinical NLP extraction assistant. Extract structured clinical information from the following encounter transcript. Return STRICT JSON ONLY (no code fences).

Schema:
{{
  "chief_complaint": "string or null",
  "symptoms": [{{"name": "string", "severity": "mild|moderate|severe|unknown", "onset": "string or null", "duration": "string or null"}}],
  "medications_mentioned": [{{"name": "string", "context": "string"}}],
  "prior_diagnoses": [{{"name": "string", "source": "patient-reported|doctor-stated"}}],
  "family_history": [{{"condition": "string", "relation": "string"}}],
  "environmental_factors": ["string"],
  "allergies": ["string"],
  "vital_observations": ["string"],
  "key_quotes": [{{"speaker": "patient|doctor|unknown", "text": "string"}}]
}}

Transcript:
{transcript}"""

        resp = client.chat.completions.create(
            model=model_used,
            response_format={"type": "json_object"},
            temperature=0.1,
            messages=[
                {"role": "system", "content": "You are a careful clinical NLP assistant. Output must be a single JSON object. Extract only what is explicitly stated in the transcript. Do not infer or assume."},
                {"role": "user", "content": prompt},
            ],
        )
        raw = (resp.choices[0].message.content or "").strip()
        extraction = json.loads(raw)
    except json.JSONDecodeError:
        extraction = {"_parse_error": "Failed to parse extraction response", "_raw": raw}
    except Exception as e:
        logger.error("Clinical extraction failed: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Extraction failed: {e}",
        )

    return {
        "extraction": extraction,
        "model": model_used,
        "patient_id": body.patient_id,
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }


class EncounterNoteRequest(BaseModel):
    transcript: str
    accepted_codes: List[Dict[str, Any]]
    extraction: Optional[Dict[str, Any]] = None
    patient_id: Optional[str] = None
    encounter_date: Optional[str] = None


@router.post("/encounter_note")
async def generate_encounter_note(
    body: EncounterNoteRequest,
    current_user: Any = Depends(get_current_user_postgres),
) -> dict:
    """
    Generate a structured encounter note from accepted codes + transcript.
    Returns JSON structure + rendered markdown.
    """
    _require_doctor(current_user)

    transcript = (body.transcript or "").strip()
    if not transcript:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Empty transcript")

    codes_text = "\n".join(
        f"- [{c.get('system', '')}] {c.get('code', '')} — {c.get('description', c.get('title', ''))}"
        for c in (body.accepted_codes or [])
    )

    extraction_text = ""
    if body.extraction:
        extraction_text = f"\nExtracted data:\n{json.dumps(body.extraction, indent=2)}"

    try:
        from openai import OpenAI
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        model_used = os.getenv("CHAT_MODEL", "gpt-4o-mini")

        prompt = f"""You are a clinical documentation assistant. Generate a structured encounter note from the following encounter data. Return STRICT JSON ONLY (no code fences).

Schema:
{{
  "chief_complaint": "string",
  "history_of_present_illness": "string (paragraph)",
  "review_of_systems": "string",
  "assessment": "string (paragraph referencing accepted codes)",
  "plan": ["string"],
  "accepted_codes_summary": [{{"system": "string", "code": "string", "title": "string"}}],
  "suggested_labs": ["string"],
  "suggested_imaging": ["string"],
  "follow_up": "string",
  "markdown": "string (full encounter note rendered as markdown)"
}}

Accepted medical codes:
{codes_text or "(none)"}

{extraction_text}

Transcript:
{transcript}"""

        resp = client.chat.completions.create(
            model=model_used,
            response_format={"type": "json_object"},
            temperature=0.2,
            messages=[
                {"role": "system", "content": "You are a careful clinical documentation assistant. Generate professional encounter notes. Output must be a single JSON object."},
                {"role": "user", "content": prompt},
            ],
        )
        raw = (resp.choices[0].message.content or "").strip()
        note = json.loads(raw)
    except json.JSONDecodeError:
        note = {"_parse_error": "Failed to parse encounter note response", "_raw": raw}
    except Exception as e:
        logger.error("Encounter note generation failed: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Encounter note generation failed: {e}",
        )

    return {
        "note": note,
        "model": model_used,
        "patient_id": body.patient_id,
        "encounter_date": body.encounter_date or datetime.utcnow().strftime("%Y-%m-%d"),
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "doctor_id": str(current_user.id),
        "doctor_name": current_user.full_name or current_user.email,
    }
