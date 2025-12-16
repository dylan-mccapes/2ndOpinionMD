# server/timeline/ingest_utils.py
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from server.timeline.models import (
    EventType,
    EventSource,
    LabResult,
    ImagingData,
    TimelineEventCreate,
)

def make_lab_event(patient_id: str, lab: Dict[str, Any]) -> TimelineEventCreate:
    ts = datetime.fromisoformat(lab["ts"])
    lr = LabResult(
        test_name=lab["test_name"],
        value=lab["value"],
        unit=lab.get("unit", ""),
        reference_range=lab.get("reference_range", ""),
        flag=lab.get("flag", "normal"),
        qualitative=lab.get("qualitative"),
    )
    meta = {
        "panel": lab.get("panel"),
        "loinc": lab.get("loinc"),
        "raw_source": lab.get("raw_source"),
    }
    text = (
        f"{lab['test_name']} {lab['value']} {lab.get('unit','')}"
        f" (ref {lab.get('reference_range','')}) flag={lab.get('flag','normal')}"
    )

    return TimelineEventCreate(
        patient_id=patient_id,
        ts=ts,
        event_type=EventType.LAB,
        source=EventSource.EHR,
        structured=lr.model_dump(),
        text=text,
        meta=meta,
    )


def make_imaging_event(patient_id: str, study: Dict[str, Any]) -> TimelineEventCreate:
    ts = datetime.fromisoformat(study["ts"])
    im = ImagingData(
        modality=study["modality"],
        body_part=study["body_part"],
        findings=study.get("findings", []),
        impression=study["impression"],
        comparison=study.get("comparison"),
    )
    meta = {
        "accession": study.get("accession"),
        "raw_source": study.get("raw_source"),
    }
    text = (
        f"{study['modality']} of {study['body_part']}."
        f" Impression: {study['impression']}"
    )

    return TimelineEventCreate(
        patient_id=patient_id,
        ts=ts,
        event_type=EventType.IMAGING,
        source=EventSource.EHR,
        structured=im.model_dump(),
        text=text,
        meta=meta,
    )
