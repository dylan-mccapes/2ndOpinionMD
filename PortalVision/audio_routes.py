"""
FastAPI routes for audio export.

Endpoints:
- POST /api/audio/export - Export artifact to audio (with consent)
- GET /api/audio/files/{audio_id} - Download audio file
- GET /api/audio/receipts - List audio export receipts
- GET /api/audio/receipts/{receipt_id} - Get specific receipt
"""

import os
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel

from PortalVision.audio_generator import AudioGenerator
from PortalVision.audio_projector import html_to_audio_text, validate_audio_text
from PortalVision.audio_receipts import AudioReceiptStore
from PortalVision.vault import EpistemicHTMLVault


# Initialize components
PORTAL_VISION_DIR = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),
    "portal_vision_data"
)
vault = EpistemicHTMLVault(vault_dir=os.path.join(PORTAL_VISION_DIR, "vault"))
audio_generator = AudioGenerator(output_dir=os.path.join(PORTAL_VISION_DIR, "audio"))
audio_receipt_store = AudioReceiptStore(receipts_dir=os.path.join(PORTAL_VISION_DIR, "receipts"))

router = APIRouter(prefix="/api/audio", tags=["audio"])


# === Request Models ===

class AudioExportRequest(BaseModel):
    artifact_id: str
    operator_id: str
    consent_phrase: str
    lang: Optional[str] = 'en'


# === Endpoints ===

@router.post("/export")
async def export_audio(request: AudioExportRequest):
    """
    Export an artifact to audio.
    
    Requirements:
    1. Artifact must exist
    2. Consent phrase must match exactly: "I consent to generate an audio projection of this artifact."
    3. Audio generation must succeed
    
    Returns:
    - receipt_id
    - audio_file_path
    - source_artifact_id
    - timestamp
    
    Note:
    - Audio is derived, not authoritative
    - HTML artifact remains the source of truth
    - Audio is verbatim narration only
    """
    # Retrieve artifact
    artifact = vault.retrieve(request.artifact_id)
    if not artifact:
        raise HTTPException(status_code=404, detail="Artifact not found")
    
    # Verify consent (exact match)
    required_consent = "I consent to generate an audio projection of this artifact."
    if request.consent_phrase != required_consent:
        raise HTTPException(
            status_code=403,
            detail=f"Consent phrase must match exactly: '{required_consent}'"
        )
    
    # Convert HTML to audio text
    try:
        audio_text = html_to_audio_text(artifact.html_content)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"HTML to text conversion failed: {str(e)}"
        )
    
    # Validate audio text
    is_valid, error_msg = validate_audio_text(audio_text)
    if not is_valid:
        raise HTTPException(
            status_code=400,
            detail=f"Audio text validation failed: {error_msg}"
        )
    
    # Generate audio
    success, audio_path, error = audio_generator.generate_audio(
        text=audio_text,
        lang=request.lang,
    )
    
    if not success:
        raise HTTPException(
            status_code=500,
            detail=f"Audio generation failed: {error}"
        )
    
    # Record receipt
    receipt = audio_receipt_store.record(
        source_artifact_id=artifact.artifact_id,
        source_artifact_hash=artifact.content_hash,
        audio_file_path=audio_path,
        operator_id=request.operator_id,
        consent_phrase=request.consent_phrase,
    )
    
    return {
        "receipt_id": receipt.receipt_id,
        "audio_file_path": audio_path,
        "source_artifact_id": receipt.source_artifact_id,
        "source_artifact_hash": receipt.source_artifact_hash,
        "timestamp": receipt.timestamp,
        "artifact_type": receipt.artifact_type,
        "authority": receipt.authority,
        "audio_is_authoritative": receipt.audio_is_authoritative,
        "transformation": receipt.transformation,
    }


@router.get("/files/{audio_id}")
async def download_audio(audio_id: str):
    """
    Download an audio file.
    
    Args:
        audio_id: The audio file ID (16-char hash)
    
    Returns:
        Audio file (mp3)
    """
    audio_path = audio_generator.get_audio_path(audio_id)
    
    if not audio_path or not audio_path.exists():
        raise HTTPException(status_code=404, detail="Audio file not found")
    
    return FileResponse(
        path=str(audio_path),
        media_type="audio/mpeg",
        filename=f"{audio_id}.mp3",
    )


@router.get("/receipts")
async def list_audio_receipts(
    artifact_id: Optional[str] = Query(None),
    operator_id: Optional[str] = Query(None),
):
    """
    List audio export receipts.
    
    Optional filters:
    - artifact_id: Show receipts for specific artifact
    - operator_id: Show receipts for specific operator
    """
    receipts = audio_receipt_store.list_receipts(
        artifact_id=artifact_id,
        operator_id=operator_id,
    )
    
    return {
        "receipts": [r.to_dict() for r in receipts],
        "count": len(receipts),
    }


@router.get("/receipts/{receipt_id}")
async def get_audio_receipt(receipt_id: str):
    """Get a specific audio export receipt by ID."""
    receipt = audio_receipt_store.get_receipt(receipt_id)
    
    if not receipt:
        raise HTTPException(status_code=404, detail="Receipt not found")
    
    return receipt.to_dict()


@router.get("/preview/{artifact_id}")
async def preview_audio_text(artifact_id: str):
    """
    Preview the text that would be converted to audio.
    
    Useful for:
    - Verifying verbatim projection
    - Checking text quality before export
    - Understanding what audio will say
    
    Returns:
    - text: The text that would be narrated
    - character_count: Length of text
    - estimated_duration_seconds: Rough estimate (150 words/min)
    """
    # Retrieve artifact
    artifact = vault.retrieve(artifact_id)
    if not artifact:
        raise HTTPException(status_code=404, detail="Artifact not found")
    
    # Convert HTML to audio text
    try:
        audio_text = html_to_audio_text(artifact.html_content)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"HTML to text conversion failed: {str(e)}"
        )
    
    # Validate
    is_valid, error_msg = validate_audio_text(audio_text)
    
    # Estimate duration (rough: 150 words per minute)
    word_count = len(audio_text.split())
    estimated_duration = (word_count / 150) * 60  # seconds
    
    return {
        "artifact_id": artifact_id,
        "text": audio_text,
        "character_count": len(audio_text),
        "word_count": word_count,
        "estimated_duration_seconds": int(estimated_duration),
        "is_valid": is_valid,
        "validation_error": error_msg if not is_valid else None,
    }

