"""
FastAPI routes for printer application.

Endpoints:
- POST /api/printer/artifacts - Store an HTML artifact
- GET /api/printer/artifacts/{artifact_id} - Retrieve an artifact
- POST /api/printer/print - Print an artifact (with consent)
- GET /api/printer/receipts - List print receipts
"""

import os
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Body, HTTPException, Query
from pydantic import BaseModel

from PortalVision.printer import Printer
from PortalVision.receipts import PrintReceiptStore
from PortalVision.vault import EpistemicHTMLVault


# Initialize vault and receipt store
PORTAL_VISION_DIR = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),
    "portal_vision_data"
)
vault = EpistemicHTMLVault(vault_dir=os.path.join(PORTAL_VISION_DIR, "vault"))
receipt_store = PrintReceiptStore(receipts_dir=os.path.join(PORTAL_VISION_DIR, "receipts"))

router = APIRouter(prefix="/api/printer", tags=["printer"])


# === Request Models ===

class StoreArtifactRequest(BaseModel):
    html_content: str
    provenance: Dict[str, Any]
    metadata: Optional[Dict[str, Any]] = None


class PrintRequest(BaseModel):
    artifact_id: str
    operator_id: str
    consent_text: str


# === Endpoints ===

@router.post("/artifacts")
async def store_artifact(request: StoreArtifactRequest):
    """
    Store an HTML artifact in the Epistemic HTML Vault.
    
    Returns artifact_id and content_hash.
    """
    artifact = vault.store(
        html_content=request.html_content,
        provenance=request.provenance,
        metadata=request.metadata,
    )
    
    return {
        "artifact_id": artifact.artifact_id,
        "content_hash": artifact.content_hash,
        "created_at": artifact.created_at,
    }


@router.get("/artifacts/{artifact_id}")
async def get_artifact(artifact_id: str):
    """Retrieve an artifact by ID."""
    artifact = vault.retrieve(artifact_id)
    
    if not artifact:
        raise HTTPException(status_code=404, detail="Artifact not found")
    
    return artifact.to_dict()


@router.get("/artifacts")
async def list_artifacts():
    """List all artifacts (metadata only)."""
    return vault.list_artifacts()


@router.post("/print")
async def print_artifact(request: PrintRequest):
    """
    Print an artifact.
    
    Requirements:
    1. Artifact must exist
    2. Consent text must match exactly: "I consent to print this artifact exactly as rendered."
    3. OS must accept print job
    
    Returns:
    - receipt_id
    - artifact_id
    - artifact_hash
    - timestamp
    
    Note: No verification of print success. OS handoff only.
    """
    # Retrieve artifact
    artifact = vault.retrieve(request.artifact_id)
    if not artifact:
        raise HTTPException(status_code=404, detail="Artifact not found")
    
    # Verify consent (exact match)
    required_consent = "I consent to print this artifact exactly as rendered."
    if request.consent_text != required_consent:
        raise HTTPException(
            status_code=403,
            detail=f"Consent text must match exactly: '{required_consent}'"
        )
    
    # Attempt print handoff
    success, error = Printer.print_html(artifact.html_content)
    if not success:
        raise HTTPException(
            status_code=500,
            detail=f"Print handoff failed: {error}"
        )
    
    # Record receipt
    receipt = receipt_store.record(
        artifact_id=artifact.artifact_id,
        artifact_hash=artifact.content_hash,
        operator_id=request.operator_id,
        consent_text=request.consent_text,
    )
    
    return {
        "receipt_id": receipt.receipt_id,
        "artifact_id": receipt.artifact_id,
        "artifact_hash": receipt.artifact_hash,
        "operator_id": receipt.operator_id,
        "timestamp": receipt.timestamp,
        "note": receipt.note,
    }


@router.get("/receipts")
async def list_receipts(
    artifact_id: Optional[str] = Query(None),
    operator_id: Optional[str] = Query(None),
):
    """
    List print receipts.
    
    Optional filters:
    - artifact_id: Show receipts for specific artifact
    - operator_id: Show receipts for specific operator
    """
    receipts = receipt_store.list_receipts(
        artifact_id=artifact_id,
        operator_id=operator_id,
    )
    
    return {
        "receipts": [r.to_dict() for r in receipts],
        "count": len(receipts),
    }


@router.get("/receipts/{receipt_id}")
async def get_receipt(receipt_id: str):
    """Get a specific receipt by ID."""
    receipt = receipt_store.get_receipt(receipt_id)
    
    if not receipt:
        raise HTTPException(status_code=404, detail="Receipt not found")
    
    return receipt.to_dict()

