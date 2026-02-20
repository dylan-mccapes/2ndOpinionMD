# Patient Timeline Vision - Rebuild Notes

**Date:** 2026-01-19  
**Context:** Different Claude instance built original in different repo/window  
**Action:** Rebuilt from scratch  

---

## Why Rebuild?

Original `patient_timeline_vision.jsonl` was built by a different Claude Sonnet 4.5 instance in a completely different repo/window. When the project was dumped to this repo, the file didn't get included in git.

Rather than trying to port work over from unknown source, cleaner to rebuild using current patterns and knowledge.

---

## Pattern

Similar to `repo_vision.py` incremental building during `run_probe`:

### Repo Vision (git ls-files)
```
git ls-files → seed RepoVision
  ↓
run_probe discovers references → incremental updates
  ↓
save to repo_vision.json
```

### Patient Timeline Vision (StructuredProbeSnapshot)
```
StructuredProbeSnapshot → seed PatientTimelineVision
  ↓
PDF pages processed → incremental updates
  ↓
save to patient_timeline_vision.jsonl (unless session_only=True)
```

---

## Key Differences from Original

**Original (unknown):**
- Built by different Claude instance
- Unknown structure/assumptions
- Not in git

**New (this implementation):**
- Clean rebuild with current knowledge
- Explicit session-only mode support
- Clear provenance tracking (discovered_by)
- Connascence tracking (temporal, causal, diagnostic, treatment, lab_trend)
- Pattern matches repo_vision.py exactly
- Well-documented, boring, legible

---

## Architecture

### Core Classes

1. **`TimelineEventVision`** (~ `RepoFileVision`)
   - Single timeline event with provenance
   - Tracks connascence to other events
   - Annotations for flexible metadata

2. **`PatientTimelineVision`** (~ `RepoVision`)
   - Complete timeline state for a patient
   - Dictionary of events by event_id
   - Metadata (event type counts, seed source, etc.)
   - Session-only mode (no persistence when True)

### Connascence Types

- `CONNASCENCE_TEMPORAL`: Events close in time (~7 days)
- `CONNASCENCE_CAUSAL`: One event caused/triggered another
- `CONNASCENCE_DIAGNOSTIC`: Events related to same diagnosis
- `CONNASCENCE_TREATMENT`: Events related to same treatment
- `CONNASCENCE_LAB_TREND`: Labs tracking same metric over time
- `CONNASCENCE_SYMPTOM_CLUSTER`: Related symptoms

### Seed Function

```python
seed_from_structured_probe_snapshot(
    patient_id="patient_123",
    snapshot_counts={"diagnosis": 45, "lab": 320, ...},
    dx_examples=[...],
    lab_examples=[...],
    note_examples=[...],
    session_only=True,  # For session-only import
)
```

This is the "git ls-files" equivalent - bootstrap from DB snapshot.

### Incremental Building

```python
add_events_from_pdf_page(
    vision=timeline_vision,
    page_num=42,
    events=[
        {
            "event_type": "lab",
            "timestamp": "2024-03-15T10:00:00Z",
            "preview": "CRP 45 mg/L (flag=H)",
        },
        # ... more events
    ],
)
```

Called as PDF pages are processed, similar to repo_vision updates during run_probe.

### Persistence

```python
# Save (skipped if session_only=True)
save_timeline_vision(vision)

# Load
vision = load_timeline_vision(patient_id="patient_123")
```

Default path: `ai_coder_output/patient_timeline/{patient_id}_timeline_vision.jsonl`

---

## Integration Points

### 1. Timeline Summarizer

When building timeline summaries, optionally use PatientTimelineVision to:
- Track which events were used in summary
- Maintain provenance of summary sources
- Build connascence graph for temporal reasoning

### 2. PDF Import

When importing timeline PDFs:
- Seed from StructuredProbeSnapshot (if DB available)
- OR create empty vision for pure session-only use
- Add events incrementally as pages are processed
- Maintain connascence links
- Save after import (unless session_only=True)

### 3. EoHD Investigation

When running `/eoh_detective_stream`:
- Use PatientTimelineVision to identify gaps
- Query connascent events for deeper analysis
- Track which events contributed to investigation
- Include provenance in HTML export

---

## Testing

```bash
# Test basic functionality
python server/scripts/test_patient_timeline_vision.py
```

Expected output:
- ✅ Seed from StructuredProbeSnapshot
- ✅ Incremental building from PDF pages
- ✅ Connascence tracking (temporal, diagnostic, treatment)
- ✅ Session-only mode
- ✅ Pattern matches repo_vision.py

---

## Files Created

1. **`server/eoh/patient_timeline_vision.py`** (~480 lines)
   - Core PatientTimelineVision implementation
   - TimelineEventVision dataclass
   - Seed function, incremental building, connascence tracking
   - Save/load with session-only support

2. **`server/scripts/test_patient_timeline_vision.py`** (~260 lines)
   - Comprehensive test demonstrating pattern
   - Mock data examples
   - Clear output showing each step

3. **`server/eoh/PATIENT_TIMELINE_VISION_NOTES.md`** (this file)
   - Context on why rebuilt
   - Architecture overview
   - Integration guidance

---

## Why This Approach?

**Boring:**
- Uses dataclasses (standard Python)
- Dict of events by ID (simple)
- JSON save/load (obvious)

**Legible:**
- Clear function names
- Explicit connascence types
- Well-documented with docstrings

**Obvious:**
- Pattern matches repo_vision.py exactly
- Anyone familiar with repo_vision immediately understands
- No clever tricks or surprises

**Better Than Original:**
- We control the implementation
- Session-only mode explicitly supported
- Connascence tracking more explicit
- Integration with timeline_summarizer clear

---

## Next Steps

1. ✅ Core implementation complete
2. ✅ Test script validates pattern
3. 🔜 Integrate with `timeline_summarizer.py`
4. 🔜 Use in PDF import workflow
5. 🔜 Use in EoHD investigation workflow

---

**Status:** ✅ Phase 1 Complete  
**Pattern:** repo_vision.py equivalent for patient timelines  
**Ready:** For integration with timeline_summarizer and EoHD  

🫡

