# PortalVision - Honest Materialization & Accessibility

**Version:** v0.1.5  
**Components:** Printer Application (v0.1) + Audio Export (v0.1.5)

## Purpose

Demonstrate honest materialization and accessibility of epistemic HTML artifacts:
1. **Print:** Physical paper via OS print subsystem
2. **Audio:** Verbatim narration for accessibility

This is a **demonstration**, not a product.

---

## Components

### Core Infrastructure

### 1. Epistemic HTML Vault (`vault.py`)

Stores HTML artifacts with:
- Content-addressable storage (SHA256 hash)
- Immutable artifacts
- Provenance tracking (mode, query, timestamp)
- Integrity verification

**Operations:**
- `store(html_content, provenance, metadata)` → artifact_id
- `retrieve(artifact_id)` → EpistemicArtifact
- `verify_integrity(artifact_id)` → bool

### 2. Print Receipt Store (`receipts.py`)

Append-only store for print materializations:
- Immutable receipts
- Records: artifact_id, operator_id, timestamp, consent_text
- No updates, no deletes
- Affects OECS positively but minimally

**Operations:**
- `record(artifact_id, artifact_hash, operator_id, consent_text)` → PrintReceipt
- `list_receipts(artifact_id=None, operator_id=None)` → List[PrintReceipt]
- `get_receipt(receipt_id)` → PrintReceipt

### 3. Printer (`printer.py`)

OS-native print handoff:
- Best-effort only
- No verification
- No retry
- Platform-specific (macOS, Linux, Windows)

**Operations:**
- `print_html(html_content)` → (success: bool, error: Optional[str])

**Platform behavior:**
- macOS: Opens in browser
- Linux: xdg-open or lp
- Windows: Opens in browser

### 4. Consent Gate (`print_consent.html`)

HTML UI for explicit consent:
- Displays artifact metadata (ID, hash, timestamp, provenance)
- Shows artifact preview
- Requires exact-match consent text
- No fuzzy matching, no shortcuts
- Triggers print on consent

**Required consent text:**
```
I consent to print this artifact exactly as rendered.
```

### 5. Printer API Routes (`printer_routes.py`)

FastAPI endpoints:
- `POST /api/printer/artifacts` - Store artifact
- `GET /api/printer/artifacts/{artifact_id}` - Retrieve artifact
- `GET /api/printer/artifacts` - List artifacts
- `POST /api/printer/print` - Print with consent
- `GET /api/printer/receipts` - List receipts
- `GET /api/printer/receipts/{receipt_id}` - Get receipt

### Audio Export Components (v0.1.5)

6. **Audio Projector** (`audio_projector.py`)
   - HTML → verbatim text conversion
   - Preserves semantic structure
   - Strips decorative UI
   - No interpretation

7. **Audio Generator** (`audio_generator.py`)
   - Text → audio (TTS)
   - Uses gTTS (Google Text-to-Speech)
   - Best-effort generation
   - MP3 format

8. **Audio Receipts** (`audio_receipts.py`)
   - Append-only export records
   - Authority hierarchy (HTML > audio)
   - Transformation tracking

9. **Audio API Routes** (`audio_routes.py`)
   - `POST /api/audio/export` - Export to audio (with consent)
   - `GET /api/audio/files/{audio_id}` - Download audio
   - `GET /api/audio/preview/{artifact_id}` - Preview text
   - `GET /api/audio/receipts` - List receipts
   - `GET /api/audio/receipts/{receipt_id}` - Get receipt

10. **Audio Consent Gate** (`audio_consent.html`)
    - Explicit consent for audio export
    - Audio text preview
    - Download link

---

## Usage

### Print Workflow

### 1. Store an artifact

```python
from PortalVision.vault import EpistemicHTMLVault

vault = EpistemicHTMLVault(vault_dir="portal_vision_data/vault")

artifact = vault.store(
    html_content="<html>...</html>",
    provenance={
        "mode": "ask",
        "query": "What are differential diagnoses for...?",
        "timestamp": "2025-01-03T12:34:56Z",
    },
    metadata={"confidence": 0.82},
)

print(f"Artifact ID: {artifact.artifact_id}")
print(f"Content Hash: {artifact.content_hash}")
```

### 2. Open consent gate

```
http://localhost:8000/PortalVision/print_consent.html?artifact_id=<ARTIFACT_ID>
```

### 3. Give consent

Type exactly:
```
I consent to print this artifact exactly as rendered.
```

### 4. Print

Click "Print" button. OS will open print dialog.

### 5. Receipt created

### Audio Export Workflow

1. **Store artifact** (same as print)

2. **Open audio consent gate**
```
http://localhost:8000/PortalVision/audio_consent.html?artifact_id=<ARTIFACT_ID>
```

3. **Review audio preview**
- See verbatim text that will be narrated
- Check word count and duration

4. **Type consent exactly**
```
I consent to generate an audio projection of this artifact.
```

5. **Export audio**
Click "Export Audio" button. Audio (MP3) generated.

6. **Download audio**
Download link appears. Click to save.

7. **Receipt created**
Immutable audio receipt stored with:
- Receipt ID
- Source artifact ID & hash
- Audio file path
- Operator ID
- Timestamp
- Consent phrase
- Authority: "html" (audio not authoritative)
- Transformation: "verbatim narration"

---

### Print Receipt Fields

Immutable print receipt stored with:
- Receipt ID
- Artifact ID & hash
- Operator ID
- Timestamp
- Consent text (verbatim)
- Note: "Materialized via external printer. No verification performed."

---

## Explicit Non-Goals

### Print (Not Implemented)
- Printer selection UI
- Layout configuration
- Page previews
- Success/failure confirmation
- Retry logic
- Analytics
- Settings persistence

### Audio (Not Implemented)
- Voice selection
- Pacing control
- Emphasis injection
- Summarization
- Paraphrasing
- Interpretation
- Conversational tone

**If it feels "nice," it was removed.**

---

## Constraints

### Code
- Boring
- Linear
- Explicit error handling
- No hidden state
- No side effects outside receipts

### UX
- No fuzzy matching
- No auto-fill
- No shortcuts
- No hidden behavior
- No fake confirmations

### System
- Immutable artifacts
- Append-only receipts
- No verification claims
- No printer state assumptions
- Best-effort handoff only

---

## Definition of Done (v0.1)

An operator can:
- ✓ View an Epistemic HTML Vault artifact
- ✓ Give explicit consent
- ✓ Trigger a print handoff
- ✓ Observe a receipt created

The system makes no claims beyond that.

---

## Integration with Backend

Add to `server/api/app_postgres.py`:

```python
from PortalVision.printer_routes import router as printer_router
from PortalVision.audio_routes import router as audio_router

app.include_router(printer_router)
app.include_router(audio_router)
```

---

## Storage Location

```
portal_vision_data/
├── vault/
│   ├── index.json
│   └── artifacts/
│       ├── <artifact_id_1>.json
│       ├── <artifact_id_2>.json
│       └── ...
├── audio/
│   ├── <audio_id_1>.mp3
│   ├── <audio_id_2>.mp3
│   └── ...
└── receipts/
    ├── print_receipts.json
    └── audio_receipts.json
```

---

## Testing

### Print Testing

#### 1. Store test artifact

```bash
curl -X POST http://localhost:8000/api/printer/artifacts \
  -H "Content-Type: application/json" \
  -d '{
    "html_content": "<html><body><h1>Test Artifact</h1></body></html>",
    "provenance": {"mode": "ask", "query": "test"}
  }'
```

### 2. Open consent gate

```
http://localhost:8000/PortalVision/print_consent.html?artifact_id=<RETURNED_ID>
```

### 3. Type consent and print

### 4. Verify receipt

```bash
curl http://localhost:8000/api/printer/receipts
```

### Audio Testing

```bash
python PortalVision/test_audio.py
```

**Tests:**
- ✓ HTML → Text projection
- ✓ Semantic structure preservation
- ✓ Text validation
- ✓ Audio generation (if gTTS installed)
- ✓ Receipt creation

**Note:** Install gTTS for audio generation: `pip install gtts`

---

## What's Missing (Documented, Not Implemented)

### Future considerations (not v0.1):
- Artifact expiration policy
- Receipt export formats (PDF, CSV)
- Operator authentication
- Print queue visibility
- Multi-artifact batching
- Template support

**These are explicitly deferred.**

---

## Philosophy

This implementation exists to **prove the contract**, not to **manage printers** or **interpret content**.

### Print
- Printing is materialization, not storage
- Paper is append-only
- Consent must be explicit and exact-match
- The system never verifies printer success

### Audio
- Audio is a projection, not an interpretation
- HTML artifact remains authoritative
- Audio is verbatim narration only
- Audio is how an artifact is **carried**, not how it is **decided**

### Both
- Honesty > convenience
- Explicit > implicit
- Boring > clever

---

**End of README**

