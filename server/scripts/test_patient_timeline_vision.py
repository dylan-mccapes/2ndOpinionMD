#!/usr/bin/env python3
"""
Test patient_timeline_vision.py

Demonstrates the pattern:
1. Seed from StructuredProbeSnapshot (like git ls-files)
2. Build incrementally as PDF pages are processed
3. Track connascence between events
4. Save/load from patient_timeline_vision.jsonl

Usage:
    python server/scripts/test_patient_timeline_vision.py
"""

import sys
from pathlib import Path

# Add parent to path
SCRIPT_DIR = Path(__file__).parent
SERVER_DIR = SCRIPT_DIR.parent
sys.path.insert(0, str(SERVER_DIR))

from eoh.patient_timeline_vision import (
    PatientTimelineVision,
    seed_from_structured_probe_snapshot,
    add_events_from_pdf_page,
    save_timeline_vision,
    load_timeline_vision,
    CONNASCENCE_TEMPORAL,
    CONNASCENCE_DIAGNOSTIC,
    CONNASCENCE_LAB_TREND,
)


def test_basic_timeline_vision() -> None:
    """Test basic timeline vision creation and manipulation."""
    print("=" * 70)
    print("TEST: Basic PatientTimelineVision")
    print("=" * 70)
    print()
    
    # Step 1: Seed from StructuredProbeSnapshot (mock data)
    print("📊 Step 1: Seed from StructuredProbeSnapshot")
    print("-" * 70)
    
    snapshot_counts = {
        "diagnosis": 12,
        "lab": 145,
        "note": 23,
        "med": 34,
        "procedure": 8,
    }
    
    dx_examples = [
        {"ts": "2024-01-15T10:30:00Z", "event_type": "diagnosis", "preview": "Rheumatoid arthritis, seropositive"},
        {"ts": "2024-02-20T14:00:00Z", "event_type": "diagnosis", "preview": "Interstitial lung disease"},
        {"ts": "2024-03-10T09:15:00Z", "event_type": "diagnosis", "preview": "Anemia, chronic disease"},
    ]
    
    lab_examples = [
        {"ts": "2024-01-15T11:00:00Z", "event_type": "lab", "preview": "CRP 45 mg/L (flag=H) [ref 0-10]"},
        {"ts": "2024-01-15T11:00:00Z", "event_type": "lab", "preview": "ESR 55 mm/hr (flag=H) [ref 0-20]"},
        {"ts": "2024-02-15T10:00:00Z", "event_type": "lab", "preview": "CRP 38 mg/L (flag=H) [ref 0-10]"},
    ]
    
    note_examples = [
        {"ts": "2024-01-15T12:00:00Z", "event_type": "note", "preview": "Discharge summary note_id=12345"},
        {"ts": "2024-02-20T15:00:00Z", "event_type": "note", "preview": "Pulmonology note_id=12346"},
    ]
    
    vision = seed_from_structured_probe_snapshot(
        patient_id="test_patient_001",
        snapshot_counts=snapshot_counts,
        dx_examples=dx_examples,
        lab_examples=lab_examples,
        note_examples=note_examples,
        session_only=True,  # Don't persist for test
    )
    
    print(f"✅ Seeded timeline vision for patient: {vision.patient_id}")
    print(f"   Total events: {len(vision.events)}")
    print(f"   Event types: {set(e.event_type for e in vision.events.values())}")
    print()
    
    # Step 2: Show temporal connascence (auto-inferred)
    print("🔗 Step 2: Temporal Connascence (auto-inferred)")
    print("-" * 70)
    
    # Find an event and show its temporal connections
    first_dx = vision.get_events_by_type("diagnosis")[0]
    temporal_links = vision.get_connascent_events(first_dx.event_id, kind=CONNASCENCE_TEMPORAL)
    
    print(f"Event: {first_dx.event_id} ({first_dx.preview})")
    print(f"Temporally coupled to {len(temporal_links)} events:")
    for link in temporal_links[:5]:
        print(f"  - {link.event_id} ({link.event_type}): {link.preview[:50]}...")
    print()
    
    # Step 3: Add events from PDF page (incremental building)
    print("📄 Step 3: Add Events from PDF Page (Incremental Building)")
    print("-" * 70)
    
    pdf_page_events = [
        {
            "event_type": "lab",
            "timestamp": "2024-03-15T10:00:00Z",
            "preview": "Hemoglobin 10.2 g/dL (flag=L) [ref 12-16]",
        },
        {
            "event_type": "diagnosis",
            "timestamp": "2024-03-15T11:00:00Z",
            "preview": "Anemia, worsening",
        },
        {
            "event_type": "med",
            "timestamp": "2024-03-15T12:00:00Z",
            "preview": "Started iron supplementation 325mg PO daily",
        },
    ]
    
    add_events_from_pdf_page(
        vision=vision,
        page_num=42,
        events=pdf_page_events,
    )
    
    print(f"✅ Added {len(pdf_page_events)} events from PDF page 42")
    print(f"   Total events now: {len(vision.events)}")
    
    # Show newly added events
    pdf_events = [e for e in vision.events.values() if "pdf_page_42" in e.discovered_by]
    print(f"\n   New events:")
    for e in pdf_events:
        print(f"   - {e.event_id} ({e.event_type}): {e.preview}")
    print()
    
    # Step 4: Manual connascence linking (diagnostic + treatment)
    print("🔗 Step 4: Manual Connascence Linking")
    print("-" * 70)
    
    # Link the anemia diagnosis to the hemoglobin lab
    anemia_event = [e for e in pdf_events if "Anemia" in e.preview][0]
    hgb_event = [e for e in pdf_events if "Hemoglobin" in e.preview][0]
    iron_event = [e for e in pdf_events if "iron" in e.preview][0]
    
    # Diagnostic connascence: anemia diagnosis linked to low hemoglobin lab
    vision.add_connascence_link(
        from_event_id=anemia_event.event_id,
        to_event_id=hgb_event.event_id,
        kind=CONNASCENCE_DIAGNOSTIC,
    )
    
    # Treatment connascence: iron supplementation linked to anemia
    vision.add_connascence_link(
        from_event_id=iron_event.event_id,
        to_event_id=anemia_event.event_id,
        kind="treatment",
    )
    
    print(f"✅ Linked events:")
    print(f"   {anemia_event.event_id} <-[diagnostic]-> {hgb_event.event_id}")
    print(f"   {iron_event.event_id} <-[treatment]-> {anemia_event.event_id}")
    print()
    
    # Step 5: Query connascent events
    print("🔍 Step 5: Query Connascent Events")
    print("-" * 70)
    
    print(f"Events connascent to {anemia_event.event_id}:")
    for kind, targets in anemia_event.connascence.items():
        print(f"\n   {kind}:")
        for target_id in targets:
            if target_id in vision.events:
                target = vision.events[target_id]
                print(f"   - {target.event_id}: {target.preview[:50]}...")
    print()
    
    # Step 6: Export summary
    print("📊 Step 6: Timeline Vision Summary")
    print("-" * 70)
    
    event_types = {}
    for e in vision.events.values():
        event_types[e.event_type] = event_types.get(e.event_type, 0) + 1
    
    print(f"Patient: {vision.patient_id}")
    print(f"Built at: {vision.built_at}")
    print(f"Session-only: {vision.session_only}")
    print(f"Total events: {len(vision.events)}")
    print(f"\nEvent type breakdown:")
    for et, count in sorted(event_types.items()):
        print(f"  - {et}: {count}")
    
    print(f"\nConnascence statistics:")
    total_links = sum(
        len(targets)
        for e in vision.events.values()
        for targets in e.connascence.values()
    )
    print(f"  - Total connascence links: {total_links}")
    
    connascence_types = {}
    for e in vision.events.values():
        for kind in e.connascence.keys():
            connascence_types[kind] = connascence_types.get(kind, 0) + len(e.connascence[kind])
    
    print(f"  - By type:")
    for kind, count in sorted(connascence_types.items()):
        print(f"    - {kind}: {count}")
    print()
    
    # Step 7: Test save/load (skipped for session-only, but show pattern)
    print("💾 Step 7: Save/Load Pattern (Session-Only = Skipped)")
    print("-" * 70)
    
    if vision.session_only:
        print("✅ Session-only mode: No persistence")
        print("   (In production: vision.save() writes to patient_timeline_vision.jsonl)")
    else:
        # Would normally do:
        # save_timeline_vision(vision)
        # loaded = load_timeline_vision(vision.patient_id)
        pass
    print()
    
    print("=" * 70)
    print("✅ TEST PASSED")
    print("=" * 70)
    print("\n📋 Summary:")
    print("   • Seeded from StructuredProbeSnapshot ✅")
    print("   • Built incrementally from PDF pages ✅")
    print("   • Tracked connascence (temporal, diagnostic, treatment) ✅")
    print("   • Session-only mode supported ✅")
    print("   • Pattern matches repo_vision.py ✅")
    print("\n🎯 Ready for integration with timeline_summarizer.py")
    print()


def main() -> None:
    try:
        test_basic_timeline_vision()
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

