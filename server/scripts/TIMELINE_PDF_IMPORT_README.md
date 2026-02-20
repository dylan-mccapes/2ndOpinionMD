# Timeline PDF Import (Session-Only)

**Status:** Phase 1 Complete (Option B implementation)  
**Pattern:** Similar to `repo_vision.py` incremental building during `run_probe`

---

## Overview

This implementation enables session-only timeline PDF import for EoHD investigation, following Option B from `OPERATION_3Pi$73MiC87MLV4UL7_EOHD.md`:

- ✅ PDF decryption (if encrypted)
- ✅ Text extraction via pypdf
- ✅ Timeline summarization via existing TimelineSummarizer
- ✅ Session-only guarantees (no DB writes)
- ✅ Password deletion after use
- 🔜 UI integration (Phase 2)

---

## Architecture

### Core Components

1. **`import_timeline_pdf.py`** - CLI tool for PDF import
   - Standalone script for testing/debugging
   - Handles decryption, extraction, session structure
   - Outputs JSON for inspection

2. **`timeline_summarizer.py::summarize_timeline_from_pdf()`** - Library function
   - Main entry point for programmatic use
   - Wraps PDF extraction
   - Delegates to existing `summarize_timeline_for_eoh()` pipeline
   - Returns `TimelineSummaries` object

3. **`test_timeline_pdf_import.py`** - Test script
   - Validates end-to-end functionality
   - Tests encrypted and unencrypted PDFs
   - Verifies session-only guarantees

### Data Flow

```
PDF File (encrypted or not)
    ↓
[decrypt_pdf_if_needed] → Password prompt (if needed) → Delete password
    ↓
[extract_timeline_text] → pypdf extraction → Clean NUL bytes
    ↓
[summarize_timeline_for_eoh] → Existing robust pipeline
    ↓
TimelineSummaries object
    ↓
EoHD investigation (/eoh_detective_stream)
    ↓
HTML export with data removal receipts
```

---

## Usage

### Option 1: CLI Tool (Testing/Debugging)

```bash
# Unencrypted PDF
python server/scripts/import_timeline_pdf.py \
    --pdf-path data/patient-timelines/example.pdf \
    --patient-id test_patient

# Encrypted PDF (will prompt for password)
python server/scripts/import_timeline_pdf.py \
    --pdf-path data/patient-timelines/encrypted.pdf \
    --patient-id test_patient

# Encrypted PDF with password provided
python server/scripts/import_timeline_pdf.py \
    --pdf-path data/patient-timelines/encrypted.pdf \
    --patient-id test_patient \
    --password SECRET

# Save session timeline JSON for inspection
python server/scripts/import_timeline_pdf.py \
    --pdf-path data/patient-timelines/example.pdf \
    --output-json /tmp/session_timeline.json
```

### Option 2: Library Function (Programmatic Use)

```python
from openai import AsyncOpenAI
from eoh.timeline_summarizer import summarize_timeline_from_pdf

# Initialize client
client = AsyncOpenAI()

# Import and summarize PDF
summaries = await summarize_timeline_from_pdf(
    client=client,
    question="Provide comprehensive timeline summary",
    pdf_path="data/patient-timelines/example.pdf",
    password="SECRET",  # Optional, will prompt if not provided
    max_tokens=2048,
    pool=None,  # No DB pool = pure in-memory
    patient_id="session_patient",
)

# Use summaries for EoHD
timeline_summary = summaries.timeline_summary
meds_labs = summaries.meds_and_labs_snapshot

# Pass to EoHD workflow
# (timeline_summary is now ready for /eoh_detective_stream)
```

### Option 3: Test Script

```bash
# Test unencrypted PDF
python server/scripts/test_timeline_pdf_import.py \
    --pdf-path data/patient-timelines/test.pdf

# Test encrypted PDF
python server/scripts/test_timeline_pdf_import.py \
    --pdf-path data/patient-timelines/encrypted.pdf \
    --password SECRET
```

---

## Session-Only Guarantees

✅ **No Disk Writes:**
- All timeline data stays in memory only
- No writes to `rag_corpus`
- No writes to `ehr.patient_timeline`

✅ **Immediate Deletion:**
- Password deleted immediately after decryption
- `del password` explicit in code

✅ **Explicit Cleanup:**
- Timeline text garbage collected after use
- No persistent state

✅ **Receipts:**
- HTML export will document all data handling
- Data removal receipts included in export

✅ **Session Scope:**
- Data not accessible across sessions
- No cross-user data leakage

---

## File Structure

```
2ndOpinionMD-MVP/server/
├── eoh/
│   └── timeline_summarizer.py          # Added summarize_timeline_from_pdf()
└── scripts/
    ├── import_timeline_pdf.py          # CLI tool
    ├── test_timeline_pdf_import.py     # Test script
    └── TIMELINE_PDF_IMPORT_README.md   # This file
```

---

## Next Steps (Phase 2: UI Integration)

1. **Add "Import Timeline PDF" button** to 3Pi$73MiC87MLV4ULT interface
   - Location: Upper right corner
   - Icon: 📄 or 📋
   - Opens file picker (PDF only)

2. **Password prompt UI**
   - Modal dialog for encrypted PDFs
   - Clear session-only messaging
   - Show data removal guarantees

3. **Upload endpoint**
   - FastAPI endpoint: `POST /api/timeline/import-pdf`
   - Accepts file upload + optional password
   - Calls `summarize_timeline_from_pdf()`
   - Returns session ID for EoHD execution

4. **EoHD integration**
   - Auto-activate EoHD mode after successful import
   - Pass timeline summary to `/eoh_detective_stream`
   - Generate HTML export with data removal receipts

5. **Timeline loaded indicator**
   - "Timeline loaded ✅" (small, upper right)
   - "Run EoHD Investigation" button becomes primary
   - "Clear Timeline" button (optional, for pre-investigation removal)

---

## Testing

### Prerequisites

1. OpenAI API key set: `export OPENAI_API_KEY=sk-...`
2. Test PDF available (encrypted or unencrypted)

### Run Tests

```bash
# Test CLI tool
python server/scripts/import_timeline_pdf.py \
    --pdf-path data/patient-timelines/NormanEricRoberts_decrypted.pdf \
    --patient-id test_patient \
    --max-pages 10

# Test library function
python server/scripts/test_timeline_pdf_import.py \
    --pdf-path data/patient-timelines/NormanEricRoberts_decrypted.pdf

# Test encrypted PDF (will prompt for password)
python server/scripts/test_timeline_pdf_import.py \
    --pdf-path data/patient-timelines/encrypted_example.pdf
```

### Expected Output

```
====================================================================
TIMELINE PDF IMPORT TEST (SESSION-ONLY)
====================================================================

PDF Path: data/patient-timelines/test.pdf
Encrypted: No / Unknown
Session-only: ENABLED (no DB writes)

📋 Test Question:
   Provide a comprehensive timeline summary for this patient.

🔄 Importing and summarizing PDF...
   (This may take 30-60 seconds for large PDFs)

====================================================================
✅ IMPORT AND SUMMARIZATION SUCCESSFUL
====================================================================

📊 Timeline Summary (excerpt):
----------------------------------------------------------------------
[Timeline summary text here]

💊 Meds & Labs Snapshot (excerpt):
----------------------------------------------------------------------
[Meds/labs snapshot here]

📈 Summary Statistics:
   Timeline summary length: 15,234 chars
   Meds/labs snapshot length: 2,456 chars

====================================================================
🎯 TEST PASSED
====================================================================

✅ Session-only guarantees maintained:
   • PDF decrypted in memory only
   • Password deleted immediately after use
   • No writes to rag_corpus or ehr.patient_timeline
   • Timeline text processed and summarized in memory
   • Ready for EoHD execution
```

---

## Troubleshooting

### "PDF not found"
- Check file path
- Use absolute path if relative path fails

### "Incorrect password"
- Verify password is correct
- Some PDFs use owner vs. user passwords (try both)

### "Failed to extract text"
- PDF may be image-based (needs OCR)
- PDF may be corrupted
- Try opening in Acrobat/Preview to verify readability

### "OPENAI_API_KEY not set"
- Set environment variable: `export OPENAI_API_KEY=sk-...`
- Or add to `.env` file

### Large PDF timeouts
- Use `--max-pages` to test with subset first
- Increase timeout in OpenAI client if needed
- Consider splitting very large PDFs (>1000 pages)

---

## Security & Privacy

### Encryption Handling
- Standard PDF password encryption (pypdf)
- No custom encryption schemes
- Password never transmitted or logged
- Explicit `del password` after use

### Session Management
- No session cookies or tokens
- Timeline data exists only during processing
- Garbage collected after use
- No cross-session data leakage

### HIPAA-Forward
- No PHI written to disk
- All processing in memory
- Data removal receipts in HTML export
- Clear user messaging about data lifecycle

---

## Design Rationale

### Why Option B?

**Semantically Correct:**
- Timeline data belongs in timeline processing, not masquerading as "guideline"
- Proper abstractions = maintainable code
- Future developers understand intent

**Better Results:**
- Full access to TimelineSummarizer's robust pipeline
- Single-pass, hierarchical, or RAG modes automatically selected
- Probe-based retrieval if DB pool provided

**Aligns with Engineering Principles:**
- "Boring, legible" = use purpose-built infrastructure
- TimelineSummarizer exists for this exact purpose
- No hacks or workarounds

**User Value:**
- Timeline summary ready immediately
- Clear provenance (users can verify reasoning)
- Better EoHD results (proper timeline analysis)

### Why Not Option A?

- Hacky (timeline ≠ guideline semantically)
- Unmaintainable (random guideline names confusing)
- Limited (RAG search < full timeline analysis)
- Violates principles (not boring, not legible)

---

## Future Enhancements

### PatientTimelineVision Integration
- Add `session_only=True` mode to PatientTimelineVision
- Implement graph-based temporal reasoning
- Enable pattern recognition across timeline
- Deferred until clear use case emerges

### UI Polish
- Progress bar during extraction
- Page count preview
- Timeline preview before running EoHD
- Export options (PDF, HTML, JSON)

### Advanced Features
- OCR for image-based PDFs
- Multi-file upload (merge timelines)
- Timeline editing/annotation
- Bookmark important events

---

**Status:** ✅ Phase 1 Complete (Option B)  
**Next:** UI Integration (Phase 2)  
**Pattern:** Session-only, in-memory, similar to `repo_vision.py`

🫡

