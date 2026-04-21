"""
Timeline Ingestion Module

Handles ingestion of patient documents into the timeline system:
- Accepts arbitrary documents (PDF text, OCR, plaintext, JSON blobs)
- Extracts timestamps (explicit or inferred)
- Extracts event types (lab, symptom, medication, flare, imaging, note)
- Normalizes into unified timeline events
- Embeds text using text-embedding-3-small
- Stores into ehr.patient_timeline

Usage:
    python -m server.timeline.ingest --patient-id X --path input/dir
"""

import argparse
import asyncio
import json
import logging
import os
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from .engine import TimelineEngine
from .models import (
    EventSource,
    EventType,
    FlareData,
    ImagingData,
    LabResult,
    MedicationData,
    SymptomData,
    TimelineEventCreate,
    VisitData,
)

logger = logging.getLogger(__name__)

# ============================================================================
# Inference Patterns for Structured Data Extraction
# ============================================================================

# Lab test patterns
LAB_PATTERNS = {
    # Inflammatory markers
    "CRP": r"(?:C-?reactive\s+protein|CRP)\s*[:\s]*(\d+\.?\d*)\s*(mg/[dL]|mg/L)?",
    "ESR": r"(?:erythrocyte\s+sedimentation\s+rate|ESR|sed\s+rate)\s*[:\s]*(\d+\.?\d*)\s*(mm/hr)?",
    "WBC": r"(?:white\s+blood\s+cell|WBC|leukocyte)\s*(?:count)?\s*[:\s]*(\d+\.?\d*)\s*(K/uL|x10\^9/L)?",
    
    # Autoimmune markers
    "RF": r"(?:rheumatoid\s+factor|RF)\s*[:\s]*(\d+\.?\d*)\s*(IU/mL)?",
    "anti_CCP": r"(?:anti-?CCP|anti-?cyclic\s+citrullinated\s+peptide|CCP\s+antibod(?:y|ies))\s*[:\s]*(\d+\.?\d*)\s*(U/mL)?",
    "ANA": r"(?:antinuclear\s+antibod(?:y|ies)|ANA)\s*[:\s]*(positive|negative|1:\d+)",
    "ANA_titer": r"ANA\s+titer\s*[:\s]*(1:\d+)",
    
    # Complement
    "complement_C3": r"(?:complement\s+)?C3\s*[:\s]*(\d+\.?\d*)\s*(mg/dL)?",
    "complement_C4": r"(?:complement\s+)?C4\s*[:\s]*(\d+\.?\d*)\s*(mg/dL)?",
    
    # Other common labs
    "hemoglobin": r"(?:hemoglobin|Hgb|Hb)\s*[:\s]*(\d+\.?\d*)\s*(g/dL)?",
    "platelet": r"(?:platelet|PLT)\s*(?:count)?\s*[:\s]*(\d+\.?\d*)\s*(K/uL)?",
    "creatinine": r"creatinine\s*[:\s]*(\d+\.?\d*)\s*(mg/dL)?",
}

# Lab reference ranges (simplified)
LAB_REFERENCE_RANGES = {
    "CRP": {"low": 0, "high": 10, "unit": "mg/L"},
    "ESR": {"low": 0, "high": 20, "unit": "mm/hr"},
    "WBC": {"low": 4.5, "high": 11.0, "unit": "K/uL"},
    "RF": {"low": 0, "high": 14, "unit": "IU/mL"},
    "anti_CCP": {"low": 0, "high": 20, "unit": "U/mL"},
    "complement_C3": {"low": 90, "high": 180, "unit": "mg/dL"},
    "complement_C4": {"low": 10, "high": 40, "unit": "mg/dL"},
}

# Symptom patterns
SYMPTOM_PATTERNS = {
    "joint_pain": [
        r"joint\s+pain",
        r"arthralgia",
        r"painful\s+joints?",
        r"(?:knee|hip|shoulder|wrist|ankle|finger|elbow)\s+pain",
    ],
    "joint_swelling": [
        r"joint\s+swelling",
        r"swollen\s+joints?",
        r"(?:knee|hip|shoulder|wrist|ankle|finger|elbow)\s+swelling",
        r"synovitis",
    ],
    "morning_stiffness": [
        r"morning\s+stiffness",
        r"stiffness\s+(?:in\s+the\s+)?morning",
        r"AM\s+stiffness",
    ],
    "fatigue": [
        r"fatigue",
        r"tired(?:ness)?",
        r"exhaustion",
        r"low\s+energy",
        r"malaise",
    ],
    "skin_rash": [
        r"rash",
        r"skin\s+(?:lesion|eruption)",
        r"malar\s+rash",
        r"butterfly\s+rash",
        r"psoriasis",
        r"psoriatic",
    ],
    "dry_eyes": [
        r"dry\s+eyes?",
        r"xerophthalmia",
        r"keratoconjunctivitis\s+sicca",
    ],
    "dry_mouth": [
        r"dry\s+mouth",
        r"xerostomia",
    ],
    "fever": [
        r"fever",
        r"febrile",
        r"temperature\s+(?:of\s+)?(\d+\.?\d*)",
    ],
    "weight_change": [
        r"weight\s+(?:loss|gain)",
        r"(?:lost|gained)\s+(\d+)\s*(?:lbs?|kg|pounds?|kilograms?)",
    ],
}

# Medication patterns
MEDICATION_PATTERNS = {
    # DMARDs
    "methotrexate": r"methotrexate|MTX|Trexall|Rheumatrex",
    "hydroxychloroquine": r"hydroxychloroquine|Plaquenil|HCQ",
    "sulfasalazine": r"sulfasalazine|Azulfidine",
    "leflunomide": r"leflunomide|Arava",
    
    # Biologics
    "adalimumab": r"adalimumab|Humira",
    "etanercept": r"etanercept|Enbrel",
    "infliximab": r"infliximab|Remicade",
    "tocilizumab": r"tocilizumab|Actemra",
    "rituximab": r"rituximab|Rituxan",
    "abatacept": r"abatacept|Orencia",
    "secukinumab": r"secukinumab|Cosentyx",
    "ustekinumab": r"ustekinumab|Stelara",
    
    # Steroids
    "prednisone": r"prednisone|Deltasone",
    "methylprednisolone": r"methylprednisolone|Medrol|Solu-Medrol",
    "dexamethasone": r"dexamethasone|Decadron",
    
    # NSAIDs
    "ibuprofen": r"ibuprofen|Advil|Motrin",
    "naproxen": r"naproxen|Aleve|Naprosyn",
    "celecoxib": r"celecoxib|Celebrex",
    "meloxicam": r"meloxicam|Mobic",
}

# Medication classification
DMARD_MEDS = {"methotrexate", "hydroxychloroquine", "sulfasalazine", "leflunomide"}
BIOLOGIC_MEDS = {
    "adalimumab", "etanercept", "infliximab", "tocilizumab", 
    "rituximab", "abatacept", "secukinumab", "ustekinumab"
}
STEROID_MEDS = {"prednisone", "methylprednisolone", "dexamethasone"}
NSAID_MEDS = {"ibuprofen", "naproxen", "celecoxib", "meloxicam"}

# Dose patterns
DOSE_PATTERN = r"(\d+\.?\d*)\s*(mg|mcg|g|ml|units?|IU)"
FREQUENCY_PATTERN = r"(once|twice|three\s+times?|daily|weekly|biweekly|monthly|every\s+\d+\s+(?:day|week|month)s?|QD|BID|TID|QID|PRN)"

# Imaging patterns
IMAGING_MODALITIES = {
    "xray": r"x-?ray|radiograph|plain\s+film",
    "mri": r"MRI|magnetic\s+resonance",
    "ct": r"CT\s+scan|computed\s+tomography|CAT\s+scan",
    "ultrasound": r"ultrasound|sonograph|US\s+(?:of|scan)",
}

IMAGING_FINDINGS = {
    "erosions": r"erosion|erosive",
    "synovitis": r"synovitis|synovial\s+(?:thickening|inflammation)",
    "joint_space_narrowing": r"joint\s+space\s+(?:narrowing|loss)",
    "effusion": r"effusion|fluid\s+collection",
    "bone_edema": r"bone\s+(?:marrow\s+)?edema",
}

# Flare patterns
FLARE_PATTERNS = [
    r"flare(?:-?up)?",
    r"exacerbation",
    r"disease\s+activity\s+(?:increased|worsened)",
    r"symptoms?\s+(?:worsened|increased|flared)",
]

# Disease activity score patterns
DAS28_PATTERN = r"DAS28(?:-?(?:CRP|ESR))?\s*[:\s]*(\d+\.?\d*)"
CDAI_PATTERN = r"CDAI\s*[:\s]*(\d+\.?\d*)"
SDAI_PATTERN = r"SDAI\s*[:\s]*(\d+\.?\d*)"

# Timestamp patterns
TIMESTAMP_PATTERNS = [
    # ISO format
    r"(\d{4}-\d{2}-\d{2}(?:T\d{2}:\d{2}:\d{2})?)",
    # US format
    r"(\d{1,2}/\d{1,2}/\d{4})",
    r"(\d{1,2}/\d{1,2}/\d{2})",
    # Written format
    r"((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+\d{1,2},?\s+\d{4})",
    r"(\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+\d{4})",
]


# ============================================================================
# Document Parser
# ============================================================================

class DocumentParser:
    """Parse documents and extract timeline events."""
    
    def __init__(self):
        self.engine = TimelineEngine()
    
    def parse_document(
        self,
        content: str,
        patient_id: str,
        source: Union[EventSource, str] = EventSource.PATIENT_UPLOAD,
        filename: Optional[str] = None,
        default_timestamp: Optional[datetime] = None,
    ) -> List[TimelineEventCreate]:
        """
        Parse a document and extract timeline events.
        
        Args:
            content: Document text content
            patient_id: Patient identifier
            source: Data source
            filename: Original filename (for metadata)
            default_timestamp: Default timestamp if none found
            
        Returns:
            List of TimelineEventCreate objects
        """
        events: List[TimelineEventCreate] = []
        
        # Try to extract timestamp from content
        timestamp = self._extract_timestamp(content) or default_timestamp or datetime.utcnow()
        
        # Detect event type and extract structured data
        event_type, structured = self._classify_and_extract(content)
        
        # Create normalized text
        text = self._normalize_text(content, event_type, structured)
        
        # Build metadata
        meta: Dict[str, Any] = {}
        if filename:
            meta["original_filename"] = filename
        meta["extraction_timestamp"] = datetime.utcnow().isoformat()
        
        events.append(TimelineEventCreate(
            patient_id=patient_id,
            ts=timestamp,
            event_type=event_type,
            source=source,
            structured=structured,
            text=text,
            meta=meta,
        ))
        
        return events
    
    def parse_json_blob(
        self,
        data: Dict[str, Any],
        patient_id: str,
        source: Union[EventSource, str] = EventSource.PATIENT_UPLOAD,
    ) -> List[TimelineEventCreate]:
        """
        Parse a JSON blob containing timeline event data.
        
        Expected format:
        {
            "ts": "2024-01-15T10:30:00Z",
            "event_type": "lab",
            "structured": {...},
            "text": "...",
            "meta": {...}
        }
        
        Or array of such objects.
        """
        events: List[TimelineEventCreate] = []
        
        # Handle array of events
        if isinstance(data, list):
            for item in data:
                events.extend(self.parse_json_blob(item, patient_id, source))
            return events
        
        # Parse single event
        ts = data.get("ts")
        if isinstance(ts, str):
            ts = self._parse_timestamp_string(ts)
        elif ts is None:
            ts = datetime.utcnow()
        
        event_type = data.get("event_type", data.get("kind", "note"))
        structured = data.get("structured", data.get("details", {}))
        text = data.get("text", data.get("summary", ""))
        meta = data.get("meta", {})
        
        events.append(TimelineEventCreate(
            patient_id=patient_id,
            ts=ts,
            event_type=event_type,
            source=source,
            structured=structured,
            text=text,
            meta=meta,
        ))
        
        return events
    
    def _extract_timestamp(self, content: str) -> Optional[datetime]:
        """Extract timestamp from document content."""
        for pattern in TIMESTAMP_PATTERNS:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                ts_str = match.group(1)
                parsed = self._parse_timestamp_string(ts_str)
                if parsed:
                    return parsed
        return None
    
    def _parse_timestamp_string(self, ts_str: str) -> Optional[datetime]:
        """Parse a timestamp string into datetime."""
        from server.utils.parse_date import parse_clinical_date
        return parse_clinical_date(ts_str)
    
    def _classify_and_extract(
        self, 
        content: str
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Classify document type and extract structured data.
        
        Returns:
            Tuple of (event_type, structured_data)
        """
        content_lower = content.lower()
        structured: Dict[str, Any] = {}
        
        # Check for lab results
        lab_data = self._extract_lab_data(content)
        if lab_data:
            return "lab", lab_data
        
        # Check for flare
        for pattern in FLARE_PATTERNS:
            if re.search(pattern, content_lower):
                flare_data = self._extract_flare_data(content)
                return "flare", flare_data
        
        # Check for medication
        med_data = self._extract_medication_data(content)
        if med_data:
            return "medication", med_data
        
        # Check for imaging
        imaging_data = self._extract_imaging_data(content)
        if imaging_data:
            return "imaging", imaging_data
        
        # Check for symptoms
        symptom_data = self._extract_symptom_data(content)
        if symptom_data:
            return "symptom", symptom_data
        
        # Check for visit/clinical note
        if any(term in content_lower for term in ["visit", "appointment", "clinic", "examination"]):
            visit_data = self._extract_visit_data(content)
            return "visit", visit_data
        
        # Default to note
        return "note", structured
    
    def _extract_lab_data(self, content: str) -> Optional[Dict[str, Any]]:
        """Extract lab result data from content."""
        lab_data: Dict[str, Any] = {}
        
        for lab_name, pattern in LAB_PATTERNS.items():
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                value = match.group(1)
                try:
                    lab_data[lab_name] = float(value)
                except ValueError:
                    lab_data[lab_name] = value
                
                # Add unit if captured
                if len(match.groups()) > 1 and match.group(2):
                    lab_data[f"{lab_name}_unit"] = match.group(2)
                
                # Add flag based on reference range
                if lab_name in LAB_REFERENCE_RANGES:
                    ref = LAB_REFERENCE_RANGES[lab_name]
                    try:
                        val = float(value)
                        if val > ref["high"]:
                            lab_data["flag"] = "H"
                        elif val < ref["low"]:
                            lab_data["flag"] = "L"
                        else:
                            lab_data["flag"] = "N"
                    except (ValueError, TypeError):
                        pass
        
        return lab_data if lab_data else None
    
    def _extract_symptom_data(self, content: str) -> Optional[Dict[str, Any]]:
        """Extract symptom data from content."""
        symptom_data: Dict[str, Any] = {}
        content_lower = content.lower()
        
        for symptom_name, patterns in SYMPTOM_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, content_lower):
                    symptom_data[symptom_name] = True
                    break
        
        # Extract severity if mentioned
        severity_match = re.search(r"severity\s*[:\s]*(\d+)\s*/?\s*10", content_lower)
        if severity_match:
            symptom_data["severity"] = int(severity_match.group(1))
        
        # Extract morning stiffness duration
        stiffness_match = re.search(
            r"(?:morning\s+)?stiffness\s+(?:for\s+)?(\d+)\s*(?:min(?:ute)?s?|hours?)",
            content_lower
        )
        if stiffness_match:
            duration = int(stiffness_match.group(1))
            if "hour" in stiffness_match.group(0):
                duration *= 60
            symptom_data["morning_stiffness_duration_min"] = duration
        
        return symptom_data if symptom_data else None
    
    def _extract_medication_data(self, content: str) -> Optional[Dict[str, Any]]:
        """Extract medication data from content."""
        med_data: Dict[str, Any] = {}
        content_lower = content.lower()
        
        # Find medication names
        for med_name, pattern in MEDICATION_PATTERNS.items():
            if re.search(pattern, content_lower):
                med_data["medication_name"] = med_name
                
                # Classify medication type
                if med_name in DMARD_MEDS:
                    med_data["is_dmard"] = True
                elif med_name in BIOLOGIC_MEDS:
                    med_data["is_biologic"] = True
                elif med_name in STEROID_MEDS:
                    med_data["is_steroid"] = True
                elif med_name in NSAID_MEDS:
                    med_data["is_nsaid"] = True
                
                break
        
        if not med_data:
            return None
        
        # Extract dose
        dose_match = re.search(DOSE_PATTERN, content_lower)
        if dose_match:
            med_data["dose"] = f"{dose_match.group(1)} {dose_match.group(2)}"
        
        # Extract frequency
        freq_match = re.search(FREQUENCY_PATTERN, content_lower)
        if freq_match:
            med_data["frequency"] = freq_match.group(1)
        
        # Detect action (started, stopped, changed)
        if any(word in content_lower for word in ["start", "began", "initiat"]):
            med_data["action"] = "started"
        elif any(word in content_lower for word in ["stop", "discontinu", "held"]):
            med_data["action"] = "stopped"
        elif any(word in content_lower for word in ["chang", "adjust", "increas", "decreas"]):
            med_data["action"] = "changed"
        
        return med_data
    
    def _extract_imaging_data(self, content: str) -> Optional[Dict[str, Any]]:
        """Extract imaging data from content."""
        imaging_data: Dict[str, Any] = {}
        content_lower = content.lower()
        
        # Detect modality
        for modality, pattern in IMAGING_MODALITIES.items():
            if re.search(pattern, content_lower):
                imaging_data["modality"] = modality
                break
        
        if not imaging_data:
            return None
        
        # Detect findings
        findings = []
        for finding, pattern in IMAGING_FINDINGS.items():
            if re.search(pattern, content_lower):
                findings.append(finding)
                imaging_data[finding] = True
        
        if findings:
            imaging_data["findings"] = findings
        
        # Extract impression (look for "impression:" section)
        impression_match = re.search(
            r"impression[:\s]+(.+?)(?:\n\n|\Z)",
            content,
            re.IGNORECASE | re.DOTALL
        )
        if impression_match:
            imaging_data["impression"] = impression_match.group(1).strip()[:500]
        
        return imaging_data
    
    def _extract_flare_data(self, content: str) -> Dict[str, Any]:
        """Extract flare event data from content."""
        flare_data: Dict[str, Any] = {}
        content_lower = content.lower()
        
        # Extract severity
        severity_match = re.search(r"severity\s*[:\s]*(\d+)\s*/?\s*10", content_lower)
        if severity_match:
            flare_data["severity"] = int(severity_match.group(1))
        
        # Extract duration
        duration_match = re.search(r"(\d+)\s*(?:day|week)s?\s*(?:of\s+)?(?:flare|symptoms?)", content_lower)
        if duration_match:
            days = int(duration_match.group(1))
            if "week" in duration_match.group(0):
                days *= 7
            flare_data["duration_days"] = days
        
        # Extract joints involved
        joints = []
        joint_patterns = [
            "knee", "hip", "shoulder", "wrist", "ankle", "finger", 
            "elbow", "hand", "foot", "spine", "neck"
        ]
        for joint in joint_patterns:
            if joint in content_lower:
                joints.append(joint)
        if joints:
            flare_data["joints_involved"] = joints
        
        # Extract disease activity scores
        das28_match = re.search(DAS28_PATTERN, content)
        if das28_match:
            flare_data["das28"] = float(das28_match.group(1))
        
        return flare_data
    
    def _extract_visit_data(self, content: str) -> Dict[str, Any]:
        """Extract clinical visit data from content."""
        visit_data: Dict[str, Any] = {}
        content_lower = content.lower()
        
        # Extract joint counts
        swollen_match = re.search(r"(\d+)\s*swollen\s*joints?", content_lower)
        if swollen_match:
            visit_data["swollen_joint_count"] = int(swollen_match.group(1))
        
        tender_match = re.search(r"(\d+)\s*tender\s*joints?", content_lower)
        if tender_match:
            visit_data["tender_joint_count"] = int(tender_match.group(1))
        
        # Extract disease activity scores
        das28_match = re.search(DAS28_PATTERN, content)
        if das28_match:
            visit_data["das28"] = float(das28_match.group(1))
        
        cdai_match = re.search(CDAI_PATTERN, content)
        if cdai_match:
            visit_data["cdai"] = float(cdai_match.group(1))
        
        # Detect visit type
        if "follow" in content_lower:
            visit_data["visit_type"] = "follow-up"
        elif "urgent" in content_lower or "emergency" in content_lower:
            visit_data["visit_type"] = "urgent"
        else:
            visit_data["visit_type"] = "routine"
        
        return visit_data
    
    def _normalize_text(
        self,
        content: str,
        event_type: str,
        structured: Dict[str, Any],
    ) -> str:
        """
        Create normalized narrative text for the event.
        
        This text will be embedded for ANN search.
        """
        # Clean up content
        text = content.strip()
        
        # Truncate if too long
        if len(text) > 2000:
            text = text[:2000] + "..."
        
        # Add structured data summary if available
        if structured:
            summary_parts = []
            
            if event_type == "lab":
                for key, value in structured.items():
                    if not key.endswith("_unit") and key != "flag":
                        summary_parts.append(f"{key}: {value}")
            
            elif event_type == "medication":
                if "medication_name" in structured:
                    summary_parts.append(f"Medication: {structured['medication_name']}")
                if "dose" in structured:
                    summary_parts.append(f"Dose: {structured['dose']}")
                if "action" in structured:
                    summary_parts.append(f"Action: {structured['action']}")
            
            elif event_type == "symptom":
                symptoms = [k for k, v in structured.items() if v is True]
                if symptoms:
                    summary_parts.append(f"Symptoms: {', '.join(symptoms)}")
            
            if summary_parts:
                text = f"{text}\n\nExtracted: {'; '.join(summary_parts)}"
        
        return text


# ============================================================================
# Directory Ingestion
# ============================================================================

class DirectoryIngestor:
    """Ingest a directory of documents into the timeline."""
    
    SUPPORTED_EXTENSIONS = {".txt", ".json", ".md", ".csv"}
    
    def __init__(self, engine: TimelineEngine, parser: DocumentParser):
        self.engine = engine
        self.parser = parser
    
    async def ingest_directory(
        self,
        session: AsyncSession,
        patient_id: str,
        directory: Path,
        source: Union[EventSource, str] = EventSource.PATIENT_UPLOAD,
        recursive: bool = True,
    ) -> Tuple[int, List[str]]:
        """
        Ingest all documents from a directory.
        
        Args:
            session: Database session
            patient_id: Patient identifier
            directory: Directory path
            source: Data source
            recursive: Whether to process subdirectories
            
        Returns:
            Tuple of (events_created, error_messages)
        """
        events_created = 0
        errors: List[str] = []
        
        # Get all files
        if recursive:
            files = list(directory.rglob("*"))
        else:
            files = list(directory.glob("*"))
        
        # Filter to supported files
        files = [f for f in files if f.is_file() and f.suffix.lower() in self.SUPPORTED_EXTENSIONS]
        
        logger.info(f"Found {len(files)} files to process in {directory}")
        
        for file_path in files:
            try:
                events = await self._process_file(
                    session, patient_id, file_path, source
                )
                events_created += len(events)
                logger.info(f"Processed {file_path.name}: {len(events)} events")
            except Exception as e:
                error_msg = f"Error processing {file_path}: {e}"
                logger.error(error_msg)
                errors.append(error_msg)
        
        return events_created, errors
    
    async def _process_file(
        self,
        session: AsyncSession,
        patient_id: str,
        file_path: Path,
        source: Union[EventSource, str],
    ) -> List[int]:
        """Process a single file and return created event IDs."""
        content = file_path.read_text(encoding="utf-8", errors="ignore")
        
        # Handle JSON files specially
        if file_path.suffix.lower() == ".json":
            try:
                data = json.loads(content)
                events = self.parser.parse_json_blob(data, patient_id, source)
            except json.JSONDecodeError:
                # Fall back to treating as text
                events = self.parser.parse_document(
                    content, patient_id, source, filename=file_path.name
                )
        else:
            events = self.parser.parse_document(
                content, patient_id, source, filename=file_path.name
            )
        
        # Store events
        event_ids = []
        for event in events:
            event_id = await self.engine.store_event(session, event)
            event_ids.append(event_id)
        
        return event_ids


# ============================================================================
# PDF Bytes Ingestion (for API upload) — dynamic batching + graph enrichment
# ============================================================================


def _extract_pdf_pages_sync(
    pdf_bytes: bytes,
    patient_id: str,
    password: Optional[str],
) -> Tuple[List[Tuple[int, str]], int]:
    """
    CPU-bound PDF text extraction (pypdf + pypdfium2). Run via asyncio.to_thread.
    """
    from io import BytesIO

    try:
        from pypdf import PdfReader
    except ImportError as e:
        raise ImportError("pypdf required for PDF ingestion") from e

    stream = BytesIO(pdf_bytes)
    pypdf_tree_ok = False
    total_pages: int = 0
    reader = None
    try:
        reader = PdfReader(stream)
        if reader.is_encrypted:
            if not password:
                raise ValueError("PDF is encrypted; password required")
            if reader.decrypt(password) == 0:
                raise ValueError("Incorrect PDF password")
        total_pages = len(reader.pages)
        pypdf_tree_ok = True
    except ValueError:
        raise
    except Exception as init_err:
        logger.warning(
            "INGEST [%s] pypdf init/page-tree failed (%s: %s) — switching to full pypdfium2 extraction",
            patient_id, type(init_err).__name__, init_err,
        )
        try:
            import pypdfium2 as pdfium
            _doc_tmp = pdfium.PdfDocument(pdf_bytes)
            total_pages = len(_doc_tmp)
            _doc_tmp.close()
        except Exception as count_err:
            raise ValueError(
                f"PDF is unreadable by both pypdf and pypdfium2. pypdf: {init_err} | pypdfium2: {count_err}"
            ) from count_err

    logger.info("INGEST [%s] PDF has %d total pages", patient_id, total_pages)
    print(f"\n{'='*70}")
    print(f"  PDF INGESTION — patient: {patient_id}")
    print(f"  total pages: {total_pages}  pdf bytes: {len(pdf_bytes):,}")
    print(f"{'='*70}")

    pages: List[Tuple[int, str]] = []
    needs_ocr: List[int] = []
    chars_total = 0

    _pdfium_doc = None
    try:
        import pypdfium2 as pdfium
        _pdfium_doc = pdfium.PdfDocument(pdf_bytes)
    except ImportError:
        if not pypdf_tree_ok:
            raise ImportError(
                "pypdf page tree is broken and pypdfium2 is not installed. "
                "Add pypdfium2>=4.30 to server/requirements.txt"
            )
        logger.warning("INGEST pypdfium2 not installed — pypdf-only extraction (some pages may be missed)")
    except Exception as pdfium_open_err:
        logger.warning("INGEST [%s] pypdfium2 failed to open document: %s", patient_id, pdfium_open_err)
        if not pypdf_tree_ok:
            raise

    def _pdfium2_page_text(idx: int) -> str:
        if _pdfium_doc is None:
            return ""
        try:
            p = _pdfium_doc[idx]
            tp = p.get_textpage()
            t = (tp.get_text_bounded() or "").strip().replace("\x00", "")
            tp.close()
            p.close()
            return t
        except Exception as e:
            logger.warning("INGEST [%s] pypdfium2 failed on page %d: %s", patient_id, idx + 1, e)
            return ""

    try:
        if pypdf_tree_ok:
            for idx, page in enumerate(reader.pages):
                try:
                    t = (page.extract_text() or "").strip().replace("\x00", "")
                except Exception as pypdf_err:
                    logger.warning(
                        "INGEST [%s] pypdf failed on page %d: %s", patient_id, idx + 1, pypdf_err
                    )
                    t = ""

                if not t:
                    t = _pdfium2_page_text(idx)
                    if t:
                        logger.info(
                            "INGEST [%s] pypdfium2 recovered page %d (%d chars)",
                            patient_id, idx + 1, len(t),
                        )

                if t:
                    pages.append((idx + 1, t))
                    chars_total += len(t)
                else:
                    needs_ocr.append(idx + 1)
        else:
            logger.info("INGEST [%s] full pypdfium2 extraction over %d pages", patient_id, total_pages)
            for idx in range(total_pages):
                t = _pdfium2_page_text(idx)
                if t:
                    pages.append((idx + 1, t))
                    chars_total += len(t)
                else:
                    needs_ocr.append(idx + 1)
    finally:
        if _pdfium_doc is not None:
            _pdfium_doc.close()

    if not pages:
        raise ValueError(
            f"No text could be extracted from PDF "
            f"({total_pages} total pages, {len(needs_ocr)} need OCR)"
        )

    if needs_ocr:
        logger.info(
            "INGEST [%s] %d page(s) yielded no text (OCR candidates): %s",
            patient_id, len(needs_ocr), needs_ocr[:20],
        )
        print(f"  pages needing OCR: {len(needs_ocr)} — {needs_ocr[:10]}")

    logger.info(
        "INGEST [%s] %d/%d pages yielded text — %s total chars",
        patient_id, len(pages), total_pages, f"{chars_total:,}",
    )
    print(
        f"  pages with text: {len(pages)}/{total_pages}\n"
        f"  total chars extracted: {chars_total:,}\n"
        f"  avg chars/page: {chars_total // max(len(pages), 1):,}"
    )
    return pages, total_pages


async def extract_pdf_pages_from_bytes(
    pdf_bytes: bytes,
    patient_id: str,
    password: Optional[str] = None,
) -> Tuple[List[Tuple[int, str]], int]:
    """Extract (page_num, text) tuples from PDF bytes without DB or LLM work."""
    return await asyncio.to_thread(_extract_pdf_pages_sync, pdf_bytes, patient_id, password)


async def ingest_extracted_pdf_pages(
    db: AsyncSession,
    patient_id: str,
    pages: List[Tuple[int, str]],
    total_pages: int,
    *,
    pool: Any = None,
    source_filename: str = "uploaded.pdf",
    enable_timeline_rows: bool = True,
    enable_graph_enrichment: bool = True,
    ingestion_model: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Regex timeline rows + ``populate_vision_from_extracted_pages`` on already-extracted
    PDF pages. When ``pool`` is set (vault / Epistemic flow), load and merge into
    ``ehr.patient_graph_vision``; otherwise save JSONL to disk (JWT import-pdf flow).
    """
    from server.api.stream_config import (
        INGESTION_MODEL as _DEFAULT_INGESTION_MODEL,
        INGESTION_GPT41_CONTEXT_TOKENS,
        INGESTION_OLLAMA_CONTEXT_TOKENS,
        OLLAMA_BASE_URL,
    )
    from server.eoh.timeline_summarizer import populate_vision_from_extracted_pages
    from server.llm.llm_client import get_ollama_client
    from openai import AsyncOpenAI

    effective_model = ingestion_model if ingestion_model is not None else _DEFAULT_INGESTION_MODEL
    _use_openai = "gpt" in effective_model.lower()
    ingestion_context_tokens: Optional[int] = None
    if _use_openai:
        ingestion_context_tokens = INGESTION_GPT41_CONTEXT_TOKENS
    else:
        # Same default as streaming ingest + ``INGESTION_OLLAMA_CONTEXT_TOKENS``
        # (32k for eoh-llama3.1:8b). ``INGESTION_CONTEXT_TOKENS`` overrides both
        # packing and Ollama ``num_ctx`` when passed through to the summarizer.
        _raw_ctx = (os.getenv("INGESTION_CONTEXT_TOKENS") or "").strip()
        ingestion_context_tokens = (
            int(_raw_ctx) if _raw_ctx else int(INGESTION_OLLAMA_CONTEXT_TOKENS)
        )

    logger.info(
        "INGEST [%s] PTV pipeline model=%s (openai=%s ctx_tokens=%s)",
        patient_id, effective_model, _use_openai, ingestion_context_tokens,
    )
    print(
        f"  PTV / extraction model: {effective_model}\n"
        f"  (premium toggle or INGESTION_MODEL=gpt-4.1 — default env is local Ollama)"
    )

    parser = DocumentParser()
    engine = TimelineEngine()
    events_stored = 0
    enrichment_stats_list: List[Dict[str, Any]] = []
    vision = None
    vision_batches = 0
    heuristic_events_added: Optional[int] = None
    llm_events_total: Optional[int] = None

    if enable_graph_enrichment:
        if pool is not None:
            from server.eoh.patient_timeline_vision import load_timeline_vision_pg
            from server.eoh.ptv_journal_bridge import empty_user_vision

            vision = await load_timeline_vision_pg(pool, patient_id)
            if vision is None:
                vision = empty_user_vision(patient_id)
            vision.metadata = vision.metadata or {}
            vision.metadata["last_pdf_ingest"] = {
                "filename": source_filename,
                "total_pages": total_pages,
            }
        else:
            from server.eoh.patient_timeline_vision import PatientTimelineVision

            vision = PatientTimelineVision(
                patient_id=patient_id,
                built_at=datetime.now().isoformat(),
                session_only=False,
                metadata={
                    "source": "pdf_ingestion",
                    "total_pages": total_pages,
                    "filename": source_filename,
                },
            )

    # Pre-compute the chapter plan so each regex timeline row, each graph event,
    # and the OCR-pending queue all share one chapter_id. The sectionizer is
    # pure and cheap — doing it here once keeps the legacy non-streaming
    # ingest_extracted_pdf_pages and the streaming sibling in sync.
    from server.timeline.pdf_sectionizer import sectionize_pages

    chapters = sectionize_pages(pages)
    page_chapter_meta: Dict[int, Dict[str, Any]] = {}
    ocr_pending_pages: List[int] = []
    for ch in chapters:
        meta_for_pages = {
            "chapter_id": ch.chapter_id,
            "chapter_kind": ch.kind,
            "chapter_label": ch.label,
        }
        if ch.encounter_date:
            meta_for_pages["encounter_date"] = ch.encounter_date
        if ch.encounter_type:
            meta_for_pages["encounter_type"] = ch.encounter_type
        if ch.encounter_type_raw:
            meta_for_pages["encounter_type_raw"] = ch.encounter_type_raw
        if ch.section_header:
            meta_for_pages["section_header"] = ch.section_header
        for pn in ch.pages:
            page_chapter_meta[pn] = dict(meta_for_pages)
        for pn in ch.ocr_pending_pages:
            page_chapter_meta[pn] = dict(meta_for_pages)
            page_chapter_meta[pn]["needs_ocr"] = True
            page_chapter_meta[pn]["ocr_status"] = "queued"
            ocr_pending_pages.append(pn)

    if enable_timeline_rows:
        for pn, txt in pages:
            page_text = f"=== Page {pn} ===\n{txt}"
            page_events = parser.parse_document(
                page_text,
                patient_id,
                source=EventSource.PATIENT_UPLOAD,
                filename=source_filename,
            )
            for event in page_events:
                event.meta = event.meta or {}
                event.meta["page"] = pn
                # Stamp chapter context so downstream queries can filter/group by
                # clinical encounter (``WHERE meta->>'chapter_id' = ...``).
                ch_meta = page_chapter_meta.get(pn)
                if ch_meta:
                    for k, v in ch_meta.items():
                        event.meta.setdefault(k, v)
                await engine.store_event(db, event)
                events_stored += 1

            if events_stored % 500 == 0:
                logger.info("INGEST [%s] stored %d regex timeline rows so far…", patient_id, events_stored)

        logger.info(
            "INGEST [%s] stored %d regex timeline rows over %d chapter(s) "
            "(ehr.patient_timeline); ocr_pending=%d",
            patient_id,
            events_stored,
            len(chapters),
            len(ocr_pending_pages),
        )

    if enable_graph_enrichment and vision is not None:
        if _use_openai:
            ingestion_client = AsyncOpenAI()
        else:
            ingestion_client = get_ollama_client(base_url=OLLAMA_BASE_URL)

        _conc = int(os.getenv("INGESTION_EXTRACTION_CONCURRENCY", "1"))
        pop_stats = await populate_vision_from_extracted_pages(
            vision=vision,
            extraction_pages=pages,
            ingestion_client=ingestion_client,
            ingestion_model=effective_model,
            ingestion_context_tokens=ingestion_context_tokens,
            extraction_concurrency=max(1, _conc),
        )
        enrichment_stats_list = pop_stats.get("enrichment_stats") or []
        vision_batches = int(pop_stats.get("batches") or 0)
        heuristic_events_added = pop_stats.get("heuristic_events_added")
        llm_events_total = pop_stats.get("llm_events_total")
        logger.info(
            "INGEST [%s] PTV populate done — heuristic=%s LLM_events=%s batches=%s edges=%s",
            patient_id,
            heuristic_events_added,
            llm_events_total,
            vision_batches,
            vision.count_edges(),
        )
        print(
            f"\n  PTV graph (run-script algorithm): {len(vision.events)} events, "
            f"{vision.count_edges()} edges  |  LLM batches: {vision_batches}"
        )

    await db.commit()

    if vision is not None:
        if pool is not None:
            from server.eoh.patient_timeline_vision import save_timeline_vision_pg

            await save_timeline_vision_pg(pool, vision)
            logger.info(
                "INGEST [%s] final graph: %d events, %d edges — saved to Postgres",
                patient_id, len(vision.events), vision.count_edges(),
            )
        else:
            from server.eoh.patient_timeline_vision import save_timeline_vision

            save_timeline_vision(vision)
            logger.info(
                "INGEST [%s] final graph: %d events, %d edges — saved to disk",
                patient_id, len(vision.events), vision.count_edges(),
            )

    logger.info(
        "INGEST [%s] ingest_extracted_pdf_pages done — %d SQL rows, %d LLM batches",
        patient_id,
        events_stored,
        vision_batches,
    )

    return {
        "events_stored": events_stored,
        "total_pages": total_pages,
        "pages_with_text": len(pages),
        "batches": vision_batches,
        "enrichment_stats": enrichment_stats_list,
        "vision": vision,
        "heuristic_events_added": heuristic_events_added,
        "llm_events_total": llm_events_total,
        "chapters": [ch.to_dict() for ch in chapters],
        "ocr_pending_pages": list(ocr_pending_pages),
    }


async def stream_ingest_extracted_pdf_pages(
    db: AsyncSession,
    patient_id: str,
    pages: List[Tuple[int, str]],
    total_pages: int,
    *,
    pool: Any = None,
    source_filename: str = "uploaded.pdf",
    enable_timeline_rows: bool = True,
    ingestion_model: Optional[str] = None,
):
    """
    Async-generator sibling of :func:`ingest_extracted_pdf_pages`.

    Emits SSE-ready dict frames in the following order:

        1. ``{"type": "stage", "stage": "regex_rows", ...}`` — regex timeline rows
           stored, one frame per 500 rows + a final summary.
        2. ``{"type": "plan", ...}`` through ``{"type": "done", ...}`` forwarded
           from :func:`stream_populate_vision_from_extracted_pages`.
        3. ``{"type": "persisted", ...}`` — final Postgres write confirmation
           with graph event / edge counts and OCR queue size.

    Chapter metadata (``chapter_id``, ``encounter_date``, ``encounter_type``,
    ``section_header``, ``chapter_kind``) is stamped on every row and every
    graph event so downstream queries can group by clinical encounter.
    """
    from server.api.stream_config import (
        INGESTION_MODEL as _DEFAULT_INGESTION_MODEL,
        INGESTION_GPT41_CONTEXT_TOKENS,
        INGESTION_OLLAMA_CONTEXT_TOKENS,
        OLLAMA_BASE_URL,
    )
    from server.eoh.timeline_summarizer import stream_populate_vision_from_extracted_pages
    from server.llm.llm_client import get_ollama_client
    from server.timeline.pdf_sectionizer import sectionize_pages
    from openai import AsyncOpenAI

    effective_model = ingestion_model if ingestion_model is not None else _DEFAULT_INGESTION_MODEL
    _use_openai = "gpt" in effective_model.lower()
    ingestion_context_tokens: Optional[int] = None
    if _use_openai:
        ingestion_context_tokens = INGESTION_GPT41_CONTEXT_TOKENS
    else:
        _raw_ctx = (os.getenv("INGESTION_CONTEXT_TOKENS") or "").strip()
        ingestion_context_tokens = (
            int(_raw_ctx) if _raw_ctx else int(INGESTION_OLLAMA_CONTEXT_TOKENS)
        )

    parser = DocumentParser()
    engine = TimelineEngine()

    # --- chapter plan (shared with non-streaming path) --------------------
    chapters = sectionize_pages(pages)
    page_chapter_meta: Dict[int, Dict[str, Any]] = {}
    ocr_pending_pages: List[int] = []
    for ch in chapters:
        meta_for_pages = {
            "chapter_id": ch.chapter_id,
            "chapter_kind": ch.kind,
            "chapter_label": ch.label,
        }
        if ch.encounter_date:
            meta_for_pages["encounter_date"] = ch.encounter_date
        if ch.encounter_type:
            meta_for_pages["encounter_type"] = ch.encounter_type
        if ch.encounter_type_raw:
            meta_for_pages["encounter_type_raw"] = ch.encounter_type_raw
        if ch.section_header:
            meta_for_pages["section_header"] = ch.section_header
        for pn in ch.pages:
            page_chapter_meta[pn] = dict(meta_for_pages)
        for pn in ch.ocr_pending_pages:
            page_chapter_meta[pn] = dict(meta_for_pages)
            page_chapter_meta[pn]["needs_ocr"] = True
            page_chapter_meta[pn]["ocr_status"] = "queued"
            ocr_pending_pages.append(pn)

    # --- regex timeline rows (fast, synchronous over pages) ---------------
    events_stored = 0
    if enable_timeline_rows:
        for pn, txt in pages:
            page_text = f"=== Page {pn} ===\n{txt}"
            page_events = parser.parse_document(
                page_text,
                patient_id,
                source=EventSource.PATIENT_UPLOAD,
                filename=source_filename,
            )
            for event in page_events:
                event.meta = event.meta or {}
                event.meta["page"] = pn
                ch_meta = page_chapter_meta.get(pn)
                if ch_meta:
                    for k, v in ch_meta.items():
                        event.meta.setdefault(k, v)
                await engine.store_event(db, event)
                events_stored += 1

        await db.commit()
        yield {
            "type": "stage",
            "stage": "regex_rows",
            "events_stored": events_stored,
            "chapters": len(chapters),
            "ocr_pending": len(ocr_pending_pages),
        }

    # --- load / init PatientTimelineVision --------------------------------
    if pool is not None:
        from server.eoh.patient_timeline_vision import load_timeline_vision_pg
        from server.eoh.ptv_journal_bridge import empty_user_vision

        vision = await load_timeline_vision_pg(pool, patient_id)
        if vision is None:
            vision = empty_user_vision(patient_id)
        vision.metadata = vision.metadata or {}
        vision.metadata["last_pdf_ingest"] = {
            "filename": source_filename,
            "total_pages": total_pages,
        }
    else:
        from server.eoh.patient_timeline_vision import PatientTimelineVision

        vision = PatientTimelineVision(
            patient_id=patient_id,
            built_at=datetime.now().isoformat(),
            session_only=False,
            metadata={
                "source": "pdf_ingestion",
                "total_pages": total_pages,
                "filename": source_filename,
            },
        )

    # --- LLM extraction stream --------------------------------------------
    if _use_openai:
        ingestion_client = AsyncOpenAI()
    else:
        ingestion_client = get_ollama_client(base_url=OLLAMA_BASE_URL)

    async for frame in stream_populate_vision_from_extracted_pages(
        vision=vision,
        extraction_pages=pages,
        ingestion_client=ingestion_client,
        ingestion_model=effective_model,
        ingestion_context_tokens=ingestion_context_tokens,
    ):
        if frame.get("type") == "skeleton_ready":
            # Persist the regex/heuristic baseline graph before long-running LLM
            # extraction so clients can immediately query a chapterized skeleton.
            if pool is not None:
                from server.eoh.patient_timeline_vision import save_timeline_vision_pg

                await save_timeline_vision_pg(pool, vision)
            else:
                from server.eoh.patient_timeline_vision import save_timeline_vision

                save_timeline_vision(vision)
            yield {
                "type": "skeleton_persisted",
                "patient_id": patient_id,
                "graph_events": len(vision.events),
                "graph_edges": vision.count_edges(),
                "chapters": len(chapters),
            }
        yield frame

    # --- persist graph -----------------------------------------------------
    if pool is not None:
        from server.eoh.patient_timeline_vision import save_timeline_vision_pg

        await save_timeline_vision_pg(pool, vision)
    else:
        from server.eoh.patient_timeline_vision import save_timeline_vision

        save_timeline_vision(vision)

    yield {
        "type": "persisted",
        "events_stored": events_stored,
        "graph_events": len(vision.events),
        "graph_edges": vision.count_edges(),
        "chapters": len(chapters),
        "ocr_pending_pages": list(ocr_pending_pages),
        "ingestion_model": effective_model,
    }


async def run_ingest_from_pdf_bytes(
    db: AsyncSession,
    pdf_bytes: bytes,
    patient_id: str,
    password: Optional[str] = None,
    enable_graph_enrichment: bool = True,
    ingestion_model: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Extract text from PDF bytes, parse into timeline events, store in
    ehr.patient_timeline, and optionally build PatientTimelineVision using
    the same pipeline as ``run_eohd_timeline_pdf.py`` / ``populate_vision_from_extracted_pages``:
    regex heuristics on every page, batched per-page LLM extraction (with heuristic
    hints), timestamp recovery, one temporal connascence pass, type reclassification,
    and graph timestamp sanitize.

    Model: ``INGESTION_MODEL`` env (default ``eoh-llama3.1:8b`` via ``stream_config``).
    Premium OpenAI extraction: ``INGESTION_MODEL=gpt-4.1``. Ollama tuning: ``INGESTION_CONTEXT_TOKENS`` / ``OLLAMA_NUM_CTX``.

    Returns a stats dict:
        {
            "events_stored": int,
            "total_pages": int,
            "pages_with_text": int,
            "batches": int,
            "enrichment_stats": [...],
            "vision": PatientTimelineVision (if enrichment enabled),
            "elapsed_ms": int,
        }
    """
    import time as _time

    t0 = _time.perf_counter()
    pages, total_pages = await extract_pdf_pages_from_bytes(pdf_bytes, patient_id, password)
    result = await ingest_extracted_pdf_pages(
        db,
        patient_id,
        pages,
        total_pages,
        pool=None,
        source_filename="uploaded.pdf",
        enable_timeline_rows=True,
        enable_graph_enrichment=enable_graph_enrichment,
        ingestion_model=ingestion_model,
    )
    result["elapsed_ms"] = int((_time.perf_counter() - t0) * 1000)
    logger.info(
        "INGEST [%s] COMPLETE — %d events stored, %d LLM batches, %dms",
        patient_id,
        result["events_stored"],
        result["batches"],
        result["elapsed_ms"],
    )
    print(
        f"\n{'='*70}\n"
        f"  INGESTION COMPLETE\n"
        f"  events stored: {result['events_stored']}\n"
        f"  LLM extraction batches: {result['batches']}\n"
        f"  graph events: {len(result['vision'].events) if result.get('vision') else 'N/A'}\n"
        f"  graph edges: {result['vision'].count_edges() if result.get('vision') else 'N/A'}\n"
        f"  elapsed: {result['elapsed_ms']:,}ms\n"
        f"{'='*70}"
    )
    return result


# ============================================================================
# CLI Entry Point
# ============================================================================

async def main_async(args: argparse.Namespace) -> None:
    """Async main function for CLI."""
    # Get database URL from environment
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise ValueError("DATABASE_URL environment variable not set")
    
    # Convert to async URL if needed
    if database_url.startswith("postgresql://"):
        database_url = database_url.replace("postgresql://", "postgresql+asyncpg://", 1)
    
    # Create engine and session
    engine = create_async_engine(database_url)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    # Initialize components
    timeline_engine = TimelineEngine()
    parser = DocumentParser()
    ingestor = DirectoryIngestor(timeline_engine, parser)
    
    # Process directory
    directory = Path(args.path)
    if not directory.exists():
        raise ValueError(f"Directory not found: {directory}")
    
    source = EventSource(args.source) if args.source else EventSource.PATIENT_UPLOAD
    
    async with async_session() as session:
        events_created, errors = await ingestor.ingest_directory(
            session=session,
            patient_id=args.patient_id,
            directory=directory,
            source=source,
            recursive=not args.no_recursive,
        )
    
    print(f"\nIngestion complete:")
    print(f"  Events created: {events_created}")
    print(f"  Errors: {len(errors)}")
    
    if errors:
        print("\nErrors:")
        for error in errors:
            print(f"  - {error}")


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Ingest patient documents into the timeline system",
        prog="python -m server.timeline.ingest",
    )
    
    parser.add_argument(
        "--patient-id",
        required=True,
        help="Patient identifier",
    )
    
    parser.add_argument(
        "--path",
        required=True,
        help="Path to directory containing documents",
    )
    
    parser.add_argument(
        "--source",
        choices=["patient_upload", "EHR", "synced_device", "clinician_note", "journal", "demo"],
        default="patient_upload",
        help="Data source (default: patient_upload)",
    )
    
    parser.add_argument(
        "--no-recursive",
        action="store_true",
        help="Don't process subdirectories",
    )
    
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose logging",
    )
    
    args = parser.parse_args()
    
    # Configure logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    
    # Run async main
    asyncio.run(main_async(args))


if __name__ == "__main__":
    main()
