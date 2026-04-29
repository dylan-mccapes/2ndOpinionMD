# ASK Mode Streaming Contract

**Version:** 1.0  
**Date:** 2025-01-02  
**Status:** Implemented

---

## Purpose

Streaming in ASK mode exists for **operator trust calibration**, not completeness.

The operator needs to know:
1. Execution actually started
2. Evidence was consulted
3. Work is happening
4. The answer with its limitations
5. The run completed

Everything else is noise.

---

## The Contract (5 Events)

### 1. `phase_start`

**Why:** Confirms execution began.

```json
{
  "event": "phase_start",
  "mode": "ask"
}
```

**UI Effect:**
- Status → "RUNNING"
- Footer status → "RUNNING"

**Honest:** System is running or it isn't. No ambiguity.

---

### 2. `retrieval_summary`

**Why:** Answers "Did you actually look at anything?"

```json
{
  "event": "retrieval_summary",
  "sources_considered": 7,
  "sources_used": 3,
  "confidence": "medium"
}
```

**UI Effect:**
- Status → "Evidence: 3/7 sources, confidence: medium"

**Honest:** 
- Sources considered = search space
- Sources used = what made it into context
- Confidence = retrieval quality signal, not answer quality

**Refusal:** Does NOT show raw documents, embeddings, or semantic claims.

---

### 3. `reasoning_progress` (Optional)

**Why:** Prevents "black box anxiety" during longer runs.

```json
{
  "event": "reasoning_progress",
  "step": "Synthesizing evidence"
}
```

**UI Effect:**
- Status → Single line update ("Synthesizing evidence")

**Honest:**
- Coarse progress only
- No token streaming
- No chain-of-thought leakage
- Can be throttled or omitted

**Refusal:** Does NOT show internal reasoning steps, hypothesis scoring, or decision trees.

---

### 4. `final_answer` (via `llm_chunk` / `llm_done`)

**Why:** The product.

```json
{
  "event": "llm_done",
  "text": "...[complete answer]...",
  "confidence": 0.81,
  "limitations": ["Guideline-only", "No patient timeline"]
}
```

**UI Effect:**
- Answer rendered progressively (via `llm_chunk` events)
- Final answer shown on `llm_done`
- Confidence displayed (e.g., "Confidence: 81%")
- Limitations shown explicitly in warning box

**Honest:**
- Confidence is model-reported, not inflated
- Limitations are explicit, not buried
- No promise inflation

**Refusal:** Does NOT hide uncertainty or weakness.

---

### 5. `completion`

**Why:** Closure is part of honesty.

```json
{
  "event": "completion",
  "tokens_used": 412,
  "duration_ms": 1380
}
```

**UI Effect:**
- Status → "Complete — 412 tokens, 1380ms"
- Footer status → "IDLE"
- Receipt cache finalized
- Export buttons enabled

**Honest:**
- Metrics are factual
- Status change is definitive
- No ambiguity about completion

---

## What Does NOT Stream (Yet)

These artifacts are **available** but **not streamed** in the default UI:

- Raw retrieved chunks (available in receipt cache)
- Embeddings metadata (not relevant to operator)
- Internal router decisions (implementation detail)
- Hypothesis scoring vectors (epistemic overhead)
- OECS or contribution metrics (future feature)

**Why:** Availability ≠ immediacy. The operator can inspect the receipt cache if needed, but the default view remains calm.

---

## Receipt Cache Integration

### ALL Events Captured

Every SSE event is captured in the receipt cache:

```javascript
addReceiptEvent('event', 'ask', { sse_event: data });
```

This includes:
- Contract events (phase_start, retrieval_summary, etc.)
- Internal events (context_retrieved, llm_delta, etc.)
- Warnings and errors
- Completion metadata

### Operator Access

- Click "Show Receipts" to view full event log
- Export as HTML (human-readable audit)
- Export as JSON (machine-readable handoff)

### Honesty

- No filtering (lossless capture)
- No summarization (exact events)
- No interpretation (raw payloads)
- Timestamp precision (ISO 8601)

---

## UI Behavior

### Status Progression

```
"Connecting..."
  ↓
"RUNNING" (phase_start)
  ↓
"Evidence: 3/7 sources, confidence: medium" (retrieval_summary)
  ↓
"Synthesizing evidence" (reasoning_progress, optional)
  ↓
[Answer streams progressively]
  ↓
"Complete — Confidence: 81%" (final_answer)
  ↓
"Complete — 412 tokens, 1380ms" (completion)
```

### Answer Display

- Hidden until first chunk received
- Updates on each `llm_chunk`
- Finalized on `llm_done`
- Limitations shown in warning box (yellow border)

### Error Handling

- Connection error → "Connection error"
- Status remains visible
- Button re-enabled
- Footer status → "IDLE"

---

## Transparency Panel Integration

### Before Stream
- ✓ No external calls made

### During/After Stream
- ⚠ External API call made (yellow warning)
- Timestamp updated
- Honest reflection of state change

### Mode Switch
- Resets to ✓ (new session)
- Previous stream state does not carry over

---

## Design Rationale

### Why This Contract Is Honest

1. **No Performance:** Streaming is not for show. Events are functional, not decorative.

2. **No Overload:** Only 5 event types affect UI. Everything else goes to receipt cache.

3. **No Ambiguity:** Each event has clear semantics. No vague "processing..." states.

4. **No Inflation:** Confidence and limitations are explicit. No hiding weakness.

5. **No Surprise:** Operator always knows what's happening or what failed.

### Why This Contract Is Minimal

- **Restraint:** More events ≠ better UX. Noise reduces trust.
- **Upgradeable:** Contract can expand without breaking existing behavior.
- **Calm:** Interface never panics or rushes.
- **Orthogonal:** ASK remains isolated from CODING, EoH, EoHD.

### Why This Contract Is Not Complete

**By design.** Completeness is the enemy of clarity.

- Raw chunks → Available in receipt, not displayed
- Router decisions → Implementation detail, not operator concern
- Token-by-token → Too noisy, coalesced into chunks
- Hypothesis vectors → Epistemic overhead, not clinical value

**The operator can inspect the receipt if they want depth. The default view provides calibration, not exhaustion.**

---

## Testing

### Manual Test Flow

1. Select ASK mode
2. Enter: "What are differential diagnoses for bilateral joint pain?"
3. Click "SUBMIT QUERY"
4. Watch status updates:
   - "RUNNING"
   - "Evidence: X/Y sources"
   - Answer streams progressively
   - "Complete — Confidence: X%"
5. Check limitations box (if present)
6. Click "Show Receipts" → See all SSE events
7. Click "Export JSON" → Download full audit trail

### Expected Behavior

- ✓ Status updates reflect actual events
- ✓ Answer streams without blank screen
- ✓ Limitations shown explicitly
- ✓ Completion metrics accurate
- ✓ Transparency panel shows "External call made"
- ✓ Receipt cache contains ALL events
- ✓ Export produces lossless JSON

### Failure Modes

- Connection error → "Connection error" displayed
- SSE parse error → Logged to console, receipt capture continues
- No answer received → Status stuck on last event, operator sees incomplete state

---

## Constraints (Non-Negotiable)

✓ Only contract events affect UI  
✓ ALL events captured in receipt cache  
✓ No token-by-token streaming (too noisy)  
✓ No performative transparency (no fake progress bars)  
✓ Limitations always shown when present  
✓ Confidence never inflated  
✓ Closure always explicit (completion event)  

---

## Future Enhancements (Not Now)

### Could Add Later (If Needed)

- `retrieval_refusal`: When no relevant evidence found
- `confidence_low_warning`: When confidence < threshold
- `fallback_engaged`: When primary path fails

### Will NOT Add

- Token-by-token streaming (too noisy)
- Animated progress bars (performative)
- Fake "thinking" indicators (dishonest)
- Auto-retry on failure (operator control)
- Semantic previews (premature interpretation)

---

## Changelog

### 2025-01-02 — v1.0
- Initial implementation
- 5-event honest contract
- Receipt cache integration
- Status progression defined
- Limitations display added

---

**End of Contract**

