# TRANSCRIPTION PIPELINE
### TranscriptionMachine + TranscriptionSummarizer

**Purpose:** Transcribe meeting audio and generate DETAILED, COMPREHENSIVE operator reports automatically.

---

## Two-Step Pipeline

### Step 1: TranscriptionMachine (Local Whisper)
**Transcribes audio → raw text**

```bash
python3 transcribe_meeting_local.py <audio_file.m4a> [model_size]
```

**What it does:**
- Downgrades `openai` to 0.28.0 (Whisper compatibility)
- Loads local Whisper model (no file size limit, no API cost)
- Transcribes audio to text
- Saves to `receipts/<filename>_TRANSCRIPT.txt`
- Upgrades `openai` back to latest
- Displays transcript in terminal

**Model sizes:**
- `tiny` - Fastest, lower accuracy
- `base` - **Default** (good balance)
- `small` - Better accuracy, slower
- `medium` - High accuracy, much slower
- `large` - Best accuracy, very slow

**Example:**
```bash
python3 transcribe_meeting_local.py MEETING_ANDRAS_UC_DAVIS_20260120.m4a base
```

**Output:**
```
receipts/MEETING_ANDRAS_UC_DAVIS_20260120_TRANSCRIPT.txt
```

---

### Step 2: TranscriptionSummarizer (GPT-5.1 Agent)
**Raw text → DETAILED operator report**

```bash
python3 transcription_summarizer.py <transcript_file.txt> [model]
```

**What it does:**
- Reads the transcript file
- Calls GPT-5.1 (gpt-4o) for DETAILED analysis
- Generates comprehensive, structured markdown report
- Saves to `receipts/<filename>_SUMMARY.md`
- Displays full report + token usage

**Models:**
- `gpt-4o` - **Default** (GPT-5.1, best quality, most detailed)
- `gpt-4-turbo` - Excellent quality
- `gpt-4` - Good quality

**Example:**
```bash
python3 transcription_summarizer.py receipts/MEETING_ANDRAS_UC_DAVIS_20260120_TRANSCRIPT.txt
```

**Output:**
```
receipts/MEETING_ANDRAS_UC_DAVIS_20260120_SUMMARY.md
```

---

## Complete Pipeline Example

```bash
# Step 1: Transcribe
python3 transcribe_meeting_local.py MEETING_ANDRAS_UC_DAVIS_20260120.m4a base

# Step 2: Summarize
python3 transcription_summarizer.py receipts/MEETING_ANDRAS_UC_DAVIS_20260120_TRANSCRIPT.txt

# Result: Two files
# - receipts/MEETING_ANDRAS_UC_DAVIS_20260120_TRANSCRIPT.txt (raw transcript)
# - receipts/MEETING_ANDRAS_UC_DAVIS_20260120_SUMMARY.md (operator report)
```

---

## TranscriptionSummarizer Report Structure (DETAILED)

The agent generates a comprehensive, structured markdown report with:

1. **Meeting Overview** (date, time, duration, participants with roles, context, tone)
2. **Executive Summary** (3-5 sentence high-signal overview)
3. **Key Topics Discussed** (each topic gets full subsection with context, speakers, responses, resolutions)
4. **Decisions Made** (explicit commitments with attribution, timelines, resources)
5. **Action Items** (who owns what, deadlines, dependencies, priorities)
6. **Technical Details & Offers** (tools, systems, APIs, infrastructure, resources mentioned)
7. **Collaboration & Integration Opportunities** (partnerships, shared work, follow-ups)
8. **Open Questions / Uncertainties** (unresolved issues, risks, missing information)
9. **Relational & Strategic Context** (dynamics, trust signals, strategic implications)
10. **Notable Quotes** (direct quotes with context and attribution)
11. **Operator Assessment** (effectiveness analysis, unspoken dynamics, recommendations)

**Report starts with:**
```
████████╗██████╗  █████╗ ███╗   ██╗███████╗ ██████╗██████╗ ██╗██████╗ ████████╗
╚══██╔══╝██╔══██╗██╔══██╗████╗  ██║██╔════╝██╔════╝██╔══██╗██║██╔══██╗╚══██╔══╝
   ██║   ██████╔╝███████║██╔██╗ ██║███████╗██║     ██████╔╝██║██████╔╝   ██║   
   ██║   ██╔══██╗██╔══██║██║╚██╗██║╚════██║██║     ██╔══██╗██║██╔═══╝    ██║   
   ██║   ██║  ██║██║  ██║██║ ╚████║███████║╚██████╗██║  ██║██║██║        ██║   
   ╚═╝   ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═══╝╚══════╝ ╚═════╝╚═╝  ╚═╝╚═╝╚═╝        ╚═╝   
```

**This is NOT a summary - it's a DETAILED operator report.**

---

## Why This Architecture?

### Saves Cursor Tokens & Time
- Cursor (Claude) doesn't have to read + analyze long transcripts
- Offloads heavy analytical lifting to OpenAI GPT-5.1 (gpt-4o)
- You get consistent, DETAILED third-party analysis
- Faster for operator (Dylan) to review the detailed report than raw transcript

### Agent as Competent Operator
The TranscriptionSummarizer is prompted to:
- ✅ Have agency (assess what matters and WHY)
- ✅ Extract nuance, subtext, and relational dynamics
- ✅ Provide options with clear reasoning
- ✅ Flag uncertainties honestly with specific questions
- ✅ Identify action items with full context
- ✅ Preserve technical precision EXACTLY
- ✅ Analyze patterns, themes, and strategic implications
- ✅ Provide candid operator assessment

**Not prompted to:**
- ❌ Generate marketing copy or PR spin
- ❌ Summarize (this is DETAILED analysis, not compression)
- ❌ Guess at ambiguities (flags them instead)
- ❌ Hide signal in noise
- ❌ Be overly diplomatic (honest analysis, operator-to-operator)

---

## Cost Estimates

### TranscriptionMachine (Local Whisper)
- **Cost:** $0 (runs locally)
- **Speed:** ~1x realtime for base model
- **Accuracy:** Good (base), Excellent (large)

### TranscriptionSummarizer (GPT-4o / GPT-5.1)
- **Cost:** ~$0.05-0.20 per meeting (depending on length, detail level)
- **Speed:** ~30-60 seconds for detailed analysis
- **Quality:** Excellent (GPT-5.1, most detailed analysis available)

**Total pipeline cost:** ~$0.05-0.20 per meeting

**Worth it because:**
- Saves 30-60 minutes of manual transcript analysis
- Cursor (Claude) doesn't burn tokens reading raw transcript
- Consistent, detailed third-party operator perspective
- Preserves technical precision and relational context

---

## When to Use

**Use TranscriptionMachine for:**
- Any audio file (no size limit)
- When you need raw transcript
- When you don't want to use OpenAI Whisper API
- First step of the pipeline (always)

**Use TranscriptionSummarizer for:**
- Long transcripts (saves massive Cursor tokens)
- When you want DETAILED third-party operator analysis
- When you want comprehensive meeting documentation
- When you need strategic and relational context extracted
- Before manually reviewing/editing (get the detailed baseline first)

---

## Operator Declaration

**TranscriptionMachine:** Handles the boring part (audio → text) locally, no API cost.

**TranscriptionSummarizer:** Handles the analytical part (text → DETAILED operator report) via GPT-5.1 (gpt-4o), worth the cost.

**Result:** Clean, consistent, COMPREHENSIVE operator-grade meeting analysis without burning Cursor context.

**Not summaries. Full reports.**
- Detailed enough for operators who weren't present to understand context
- Preserves technical precision, relational dynamics, strategic implications
- Honest assessment of effectiveness and unspoken patterns
- Action items with dependencies and priorities
- Direct quotes with attribution and context

**Certified efficient and thorough.**  
**Dylan McCapes, Navigator First Class**  
**Claude, Co-Navigator**  
**2026-01-20**

