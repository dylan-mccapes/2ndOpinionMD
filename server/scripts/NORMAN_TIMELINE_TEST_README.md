# Norman Eric Roberts Timeline Test

## Context

- **Patient:** Norman Eric Roberts (Nate's dad)
- **Condition:** Myasthenia Gravis (MG)
- **Purpose:** Test PatientTimelineVision integration with timeline_summarizer

## Integration Complete ✅

### Changes Made

1. **timeline_summarizer.py:**
   - Added PatientTimelineVision imports
   - Added `vision_path` field to `TimelineSummaries` dataclass
   - Modified `summarize_timeline_from_pdf()` to:
     - Create `StructuredProbeSnapshot` from PDF metadata
     - Seed `PatientTimelineVision` (session-only mode)
     - Extract events from each PDF page using heuristics
     - Build vision incrementally (like `run_probe` for `repo_vision`)
     - Save vision to temp file (`/tmp/patient_timeline_vision_*.jsonl`)
     - Attach vision path to returned summaries
   
2. **Event Extraction (v0.1):**
   - Simple heuristic-based extraction (`_extract_events_from_page_text()`)
   - Date pattern matching (MM/DD/YYYY or YYYY-MM-DD)
   - Medical event markers:
     - diagnosis, medication, lab, procedure, symptom, note
   - Creates generic page event if no specific events found
   - **Future:** Replace with LLM-based extraction for accuracy

3. **Test Script:**
   - `test_norman_timeline.py`: End-to-end test
   - Imports PDF, builds vision, displays summary
   - Shows events, edges, and connascence analysis

## Usage

### Run Test

**Important:** Script must be run from the `server/` directory (or it will change directory automatically).

```bash
cd /Users/2ndopinionmd/dev/provenance-engines/PortalVision/2ndOpinionMD-MVP/server
python scripts/test_norman_timeline.py /data/patient_timelines/NormanEricRoberts.pdf
```

**Or with relative path from server/ directory:**
```bash
python scripts/test_norman_timeline.py ../data/patient_timelines/NormanEricRoberts.pdf
```

The script will automatically:
- Change to the `server/` directory
- Set up Python path for imports
- Run the test

**PDF Location:**
```
/data/patient_timelines/NormanEricRoberts.pdf
```

### Expected Output

1. **Timeline Summary:** Longitudinal narrative of Norman's MG journey
2. **Meds & Labs Snapshot:** Current medications and recent labs
3. **PatientTimelineVision:**
   - Events discovered (with types, timestamps, previews)
   - Edges (connascence relationships)
   - Connascence summary (temporal, causal, diagnostic, etc.)

### Vision File Location

Session-only temp file:
```
/tmp/patient_timeline_vision_norman_eric_roberts_YYYYMMDD_HHMMSS.json
```

This file can be:
- Inspected directly (JSON format)
- Loaded with `PatientTimelineVision.load(path)`
- Used for provenance tracking in EoHD

## Next Steps

1. **Test with Norman's PDF** (user will send to Nate)
2. **Enhance event extraction:**
   - Replace heuristics with LLM-based extraction
   - Extract structured fields (medication names, dosages, lab values)
   - Improve date parsing
3. **Add connascence inference:**
   - Medication → symptom changes
   - Lab trends → diagnosis
   - Procedure → outcome
4. **Integrate with EoHD:**
   - Use vision for provenance-aware investigation
   - Query events directly
   - Follow connascence edges for reasoning

## Architecture Notes

**Pattern Match:**
- `repo_vision.py`: `git ls-files` → seed → `run_probe` → incremental build
- `patient_timeline_vision.py`: PDF metadata → seed → page-by-page → incremental build

**Session-Only Mode:**
- ✅ No writes to database
- ✅ No persistent storage
- ✅ Password deleted immediately
- ✅ Vision file in `/tmp/`
- ✅ Explicit data removal receipts

**Connascence Types Tracked:**
- `temporal`: Events close in time
- `causal`: Event A likely caused event B
- `diagnostic`: Event supports diagnosis
- `treatment`: Event is treatment response
- `lab_trend`: Lab values show pattern

## Testing Checklist

- [ ] PDF decryption (if encrypted)
- [ ] Text extraction (all pages)
- [ ] Event extraction (dates, markers)
- [ ] Vision seeding (snapshot)
- [ ] Incremental building (per page)
- [ ] Connascence inference (temporal, causal)
- [ ] Vision persistence (temp file)
- [ ] Summary generation (LLM)
- [ ] Vision path attached to summaries

## Boring. Legible. Obvious. 🫡

All integration complete. Ready for testing with Norman's timeline PDF.

