# Audio Export v0.1.5 — README

## Purpose

Provide a parallel audio representation of epistemic HTML artifacts for accessibility, without changing truth or authority.

**Version:** v0.1.5 (minor addition to v0.1)

---

## What Audio Export Is (and Is Not)

### Is NOT
- A convenience feature
- A UX flourish
- A replacement for reading
- A new reasoning surface
- An interpretation layer

### IS
- A parallel representation of an already-exported artifact
- A consent-based accessibility affordance
- A receipt-bearing transformation, not a mutation
- A way to lower cognitive and physical barriers without changing truth

---

## Design Principle (Load-Bearing)

**Audio is a projection of structure, not an interpretation of meaning.**

If the system cannot articulate something clearly in audio without improvising, it should not speak it.

---

## Components

| Component | File | Lines | Purpose |
|-----------|------|-------|---------|
| Audio Projector | `audio_projector.py` | 180 | HTML → verbatim text conversion |
| Audio Generator | `audio_generator.py` | 100 | Text → audio (TTS wrapper) |
| Audio Receipts | `audio_receipts.py` | 130 | Append-only export records |
| API Routes | `audio_routes.py` | 190 | FastAPI endpoints |
| Consent Gate | `audio_consent.html` | 420 | Explicit consent UI |
| Test Suite | `test_audio.py` | 280 | Automated verification |

**Total:** ~1,300 lines of honest, boring code.

---

## How It Works

### 1. HTML → Text Projection

Parses HTML in document order and:

**Preserves:**
- Headings (with level indication)
- Section boundaries
- Paragraphs
- Lists
- Explicit disclaimers
- Version labels

**Strips:**
- Decorative UI (buttons, inputs, navigation)
- Non-semantic markup (divs, spans)
- Scripts and styles
- Images (reads alt text if present)

**Guarantees:**
- No summarization
- No paraphrasing
- No emphasis injection
- Document order preserved

### 2. Text → Audio

Uses gTTS (Google Text-to-Speech) to generate audio:
- Standard voice (no customization)
- Best-effort generation
- No retry
- No quality verification
- Output: MP3 format

### 3. Receipt Creation

Every audio export produces an append-only receipt:

```json
{
  "receipt_id": "AUDIO-000001-2025-01-03T12:34:56",
  "artifact_type": "audio_projection",
  "source_artifact": "epistemic_html",
  "source_artifact_id": "...",
  "source_artifact_hash": "...",
  "audio_file_path": "...",
  "audio_is_authoritative": false,
  "authority": "html",
  "content_transformed": false,
  "transformation": "verbatim narration",
  "consent_phrase": "...",
  "operator_id": "...",
  "timestamp": "..."
}
```

**Key fields:**
- `audio_is_authoritative`: Always `false`
- `authority`: Always `"html"`
- `transformation`: Always `"verbatim narration"`
- `content_transformed`: Always `false`

This makes it impossible to confuse voice with truth.

---

## Consent Language (Exact-Match)

**Required phrase (boring, explicit):**

```
I consent to generate an audio projection of this artifact.
```

No shortcuts. No memory. No defaults.

---

## API Endpoints

```
POST   /api/audio/export              Export artifact to audio (with consent)
GET    /api/audio/files/{audio_id}    Download audio file
GET    /api/audio/preview/{artifact_id}  Preview text before export
GET    /api/audio/receipts            List audio export receipts
GET    /api/audio/receipts/{receipt_id}  Get specific receipt
```

---

## Usage

### 1. Store HTML artifact (via printer application)

```bash
curl -X POST http://localhost:8000/api/printer/artifacts \
  -H "Content-Type: application/json" \
  -d '{
    "html_content": "<html>...</html>",
    "provenance": {"mode": "ask", "query": "..."}
  }'
```

### 2. Open audio consent gate

```
http://localhost:8000/PortalVision/audio_consent.html?artifact_id=<ARTIFACT_ID>
```

### 3. Review audio text preview

- See verbatim text that will be narrated
- Check word count and estimated duration
- Verify structure preservation

### 4. Type consent exactly

```
I consent to generate an audio projection of this artifact.
```

### 5. Export audio

Click "Export Audio" button. Audio file (MP3) generated and receipt created.

### 6. Download audio

Download link appears. Click to save MP3 file.

---

## Testing

### Automated Tests

```bash
python PortalVision/test_audio.py
```

**Tests:**
- ✓ HTML → Text projection
- ✓ Semantic structure preservation
- ✓ Text validation
- ✓ Audio generation (if gTTS installed)
- ✓ Receipt creation
- ✓ End-to-end flow

### Manual Tests

1. Start API server
2. Open audio consent gate with artifact_id
3. Review audio text preview
4. Type consent phrase exactly
5. Click Export Audio
6. Verify download link appears
7. Download and play audio
8. Verify receipt created

---

## Dependencies

### Required
- FastAPI (already installed)
- Pydantic (already installed)

### Optional (for audio generation)
- `gTTS` (Google Text-to-Speech)

**Install:**
```bash
pip install gtts
```

**Without gTTS:**
- Text projection works
- Audio preview works
- Audio generation fails gracefully

---

## Explicit Non-Goals (Not Implemented)

- Voice selection
- Pacing control
- Emphasis injection
- Adaptive narration
- Conversational tone
- Summarization
- Paraphrasing
- Interpretation

**If it feels "smart," it was removed.**

---

## Accessibility Framing

This is **not charity**. This is **respect for operator sovereignty**.

Some operators:
- Process better through hearing
- Need hands-free access
- Are fatigued
- Are visually overloaded

Offering audio without forcing it is responsible.

---

## Authority Hierarchy

```
HTML Artifact
  ↑
  | (source of truth)
  |
Audio Projection
  ↓
  (derived, not authoritative)
```

**The HTML artifact remains the source of truth.**  
**Audio is how an artifact is carried, not how it is decided.**

---

## Storage Structure

```
portal_vision_data/
├── vault/
│   └── artifacts/
│       └── <artifact_id>.json       # HTML artifacts
├── audio/
│   └── <audio_id>.mp3               # Generated audio files
└── receipts/
    ├── print_receipts.json          # Print receipts
    └── audio_receipts.json          # Audio receipts
```

---

## Integration with Backend

Add to `server/api/app_postgres.py`:

```python
from PortalVision.audio_routes import router as audio_router

app.include_router(audio_router)
```

---

## Example Audio Text (From Clinical Report)

**Input HTML:**
```html
<h1>Clinical Evidence Summary</h1>
<p>Patient presents with chronic fatigue and joint pain.</p>
<h2>Differential Diagnoses</h2>
<ul>
  <li>Rheumatoid Arthritis (ICD-10: M06.9)</li>
  <li>Systemic Lupus Erythematosus (ICD-10: M32.9)</li>
</ul>
```

**Output Audio Text:**
```
Heading level 1: Clinical Evidence Summary

Patient presents with chronic fatigue and joint pain.

Heading level 2: Differential Diagnoses

List:
Item 1: Rheumatoid Arthritis (ICD-10: M06.9)
Item 2: Systemic Lupus Erythematosus (ICD-10: M32.9)
```

**Verbatim. No interpretation. Structure preserved.**

---

## Constraints (Non-Negotiable)

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

### Audio
- Verbatim only
- No summarization
- No interpretation
- No adaptive pacing
- No voice customization

---

## Known Limitations (Honest)

### By Design
1. No voice selection
2. No pacing control
3. No emphasis
4. No quality verification
5. No retry on failure
6. Standard voice only
7. No audio editing
8. No multi-language support (yet)

### Technical
1. Requires gTTS library
2. Needs network for TTS
3. MP3 format only
4. No streaming audio
5. Temp files not cleaned immediately

### Operational
1. Audio generation may be slow for long texts
2. No progress indication during generation
3. No concurrent export protection
4. No audio queue visibility

---

## Future Considerations (Not v0.1.5)

### Could Add Later
- Multiple language support
- WAV format option
- Audio streaming (instead of file download)
- Batch audio export
- Audio receipt export (PDF)
- SSML support for better pronunciation

### Will NOT Add
- Voice selection
- Tone adaptation
- Summarization
- Interpretation
- Conversational style
- Emphasis injection
- Quality scoring

---

## Why This Is v0.1.5 (Not v0.9)

- Mechanism already exists (export + receipt)
- Audio is derived, not authoritative
- No new ontology required
- No persistence model changes
- Parallel export, not semantic upgrade

**This is a minor addition, not a major feature.**

---

## Philosophy

**Audio is how an artifact is carried, not how it is decided.**

- HTML artifact: Authoritative
- Audio projection: Derived
- Receipt: Immutable record
- Consent: Explicit and exact
- Transformation: Verbatim only

---

## One-Sentence System Truth

**Audio is how an artifact is carried, not how it is decided.**

---

**End of README**

