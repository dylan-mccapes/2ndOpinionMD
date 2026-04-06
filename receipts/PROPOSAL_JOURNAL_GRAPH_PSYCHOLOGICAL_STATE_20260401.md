# PROPOSAL: journal_graph — Psychological State Beneath PTV

**Date:** 2026-04-01  
**Author:** Claude (Opus 4.6, PortalVision Agent)  
**Status:** PROPOSAL · For Founder Review  
**Scope:** New graph layer for 2ndOpinionMD that captures psychological state alongside clinical timeline

---

## The Problem

PatientTimelineVision (PTV) captures clinical events: medications, labs, diagnoses, procedures, vitals. These are things that happened to the body. They have timestamps, ICD codes, drug names, lab values.

But autoimmune patients are not just bodies. Their psychological state — stress, sleep quality, mood, social isolation, pain catastrophizing, grief, hope, fatigue perception — directly modulates disease activity. Rheumatoid arthritis flares correlate with stress. Lupus flares correlate with sleep disruption. Crohn's correlates with anxiety. The evidence is overwhelming and the clinical timeline captures none of it.

The chat graph captures conversation. It decays. It evicts. It is bounded memory for what was said.

What neither PTV nor chat_graph captures:

- "I've been dreading going to work for three weeks"
- "My daughter's wedding is in June and I'm terrified I'll flare"
- "I stopped taking the methotrexate because it made me feel like a zombie"
- "The pain isn't worse, but I've stopped caring"
- "I slept 11 hours and still feel exhausted"

These are not clinical events. They are psychological state. They do not have ICD codes. They do not fit PTV's event model. They would be evicted from the chat graph because they are not anchored to timeline events and their decay scores would drop below more clinically-anchored messages.

But they are load-bearing. They predict flares. They explain non-adherence. They reveal the patient behind the timeline.

**Paying attention is our form of love. 2OPMD loves its patients.**

---

## The Proposal: journal_graph

A third graph layer that runs **underneath** PTV, capturing psychological state that would otherwise decay out of chat_graph or never adhere to PTV's clinical event model.

### Architecture

```
┌─────────────────────────────────────────────────┐
│                  PTV Graph                       │  Clinical events: meds, labs,
│  (TimelineEventVision nodes + connascence)       │  diagnoses, procedures, vitals
├─────────────────────────────────────────────────┤
│                 chat_graph                        │  Bounded conversational memory
│  (messages, decay, eviction, anchoring to PTV)   │  with logarithmic decay
├─────────────────────────────────────────────────┤
│               journal_graph                      │  Psychological state:
│  (entries, dimensions, trend lines,              │  mood, stress, sleep, adherence,
│   connections UP to PTV, DOWN from chat)         │  social, pain perception, hope
└─────────────────────────────────────────────────┘
```

### Node Types

#### JournalEntry
The primary node. Created when the patient journals through the app.

```python
@dataclass
class JournalEntry:
    entry_id: str
    patient_id: str
    created_at: str               # ISO 8601
    source: str                   # "free_text", "prompt_response", "voice_note", "mood_check"
    raw_content: str              # What the patient actually said/wrote
    
    # Dimensional scores (0.0 to 1.0, extracted by heuristic + LLM)
    dimensions: Dict[str, float]  # mood, stress, sleep, pain, energy, social, adherence, hope
    
    # Connections
    anchored_ptv_events: List[str]   # PTV event IDs this entry relates to
    promoted_from_chat: Optional[str] # chat_graph message_id if promoted from chat
    
    # Decay (slower than chat_graph — journal entries are the patient's voice)
    decay_score: float = 1.0
    retention_reason: str = "journal_entry"
    
    # Trend participation
    trend_window_days: int = 30      # How many days this entry contributes to trend
```

#### PsychDimension
The axes we track. Not diagnostic. Observational.

| Dimension | What It Captures | Why It Matters for Autoimmune |
|-----------|-----------------|-------------------------------|
| `mood` | General emotional valence | Depression predicts RA flare; mania predicts medication non-adherence |
| `stress` | Perceived stress level | Cortisol → immune dysregulation → flare |
| `sleep` | Sleep quality + duration | Sleep disruption → IL-6 elevation → inflammation |
| `pain` | Pain perception (not clinical pain score) | Catastrophizing amplifies pain experience independent of inflammation |
| `energy` | Fatigue / energy level | Fatigue is the #1 patient complaint in autoimmune; often invisible to labs |
| `social` | Social connection / isolation | Isolation → stress → flare; social support → resilience |
| `adherence` | Medication adherence (self-reported) | Non-adherence is the #1 cause of treatment failure; usually hidden |
| `hope` | Future orientation / agency | Hope predicts treatment engagement; despair predicts dropout |

#### TrendLine
Aggregated signal over time windows. This is where journal_graph becomes clinically useful.

```python
@dataclass
class TrendLine:
    patient_id: str
    dimension: str          # "mood", "stress", etc.
    window_days: int        # 7, 14, 30
    data_points: List[Tuple[str, float]]  # (date, score)
    slope: float            # Positive = improving, negative = declining
    variance: float         # High variance = unstable
    last_updated: str
```

### Connection to PTV

journal_graph connects UP to PTV through two mechanisms:

**1. Explicit anchoring:** Patient says "I've been stressed since the prednisone taper." The system anchors this journal entry to the prednisone taper event in PTV.

**2. Temporal correlation:** The trend engine computes correlations between journal dimensions and PTV events within a window. If stress trend spikes 2 weeks before every documented flare, that correlation becomes a connascence entry in the PTV graph:

```json
{
    "connascence_type": "co_variation",
    "entity_a": "journal_trend_stress",
    "entity_b": "ptv_event_ra_flare_20260315",
    "coupling_strength": 0.72,
    "evidence": "Stress trend spike preceded flare by 12 ± 3 days in 4/5 documented flares",
    "ambiguity": "Correlation window is wide; stress may be effect not cause"
}
```

### Connection from chat_graph

When the chat graph is about to evict a message, journal_graph can **promote** it:

1. Chat message has decay_score below eviction threshold
2. Before eviction, the system checks: does this message contain psychological state?
3. If yes, create a JournalEntry from it with `promoted_from_chat` reference
4. The content persists in journal_graph with slower decay
5. The chat message is evicted normally (bounded memory stays bounded)

This is how "I stopped taking the methotrexate because it made me feel like a zombie" survives eviction. It is not clinically anchored (no PTV event). It would be evicted from chat. But it is psychological state — adherence dimension — and journal_graph preserves it.

### Decay Model

journal_graph decays slower than chat_graph:

| Layer | Decay Half-life | Rationale |
|-------|----------------|-----------|
| chat_graph | ~24 hours | Conversation is ephemeral; only anchored messages persist |
| journal_graph | ~14 days | Psychological state changes slowly; trends need >7 days of data |
| PTV | No decay | Clinical events are permanent medical record |

### Enrichment Integration

During EoHD detective runs:

1. **chat_graph** provides recent conversational context (what was said)
2. **journal_graph** provides psychological trend context (how the patient is doing over time)
3. **PTV** provides clinical context (what happened medically)

The detective prompt receives all three:

```
PATIENT PSYCHOLOGICAL STATE (journal_graph, last 30 days):
  Mood: 0.6 → 0.4 (declining, slope: -0.007/day)
  Stress: 0.3 → 0.7 (rising sharply, slope: +0.013/day)  
  Sleep: stable at 0.5
  Adherence: 0.9 → 0.6 (concerning decline)
  
  Key journal entries:
  - 2026-03-20: "I've been dreading going to work" (stress: 0.8, mood: 0.3)
  - 2026-03-25: "Stopped the methotrexate, makes me feel like a zombie" (adherence: 0.1)
  - 2026-03-30: "The pain isn't worse but I've stopped caring" (hope: 0.2, energy: 0.3)
```

The detective can now connect: methotrexate non-adherence + rising stress + declining hope → high risk for disease progression that labs alone would miss.

### SQL Schema

```sql
CREATE TABLE IF NOT EXISTS ehr.journal_graph (
    entry_id        UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    patient_id      TEXT NOT NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    source          TEXT NOT NULL CHECK (source IN (
        'free_text', 'prompt_response', 'voice_note', 'mood_check', 'promoted_from_chat'
    )),
    raw_content     TEXT NOT NULL,
    
    -- Dimensional scores (0.0 to 1.0)
    dim_mood        REAL,
    dim_stress      REAL,
    dim_sleep       REAL,
    dim_pain        REAL,
    dim_energy      REAL,
    dim_social      REAL,
    dim_adherence   REAL,
    dim_hope        REAL,
    
    -- Connections
    anchored_ptv_events TEXT[] DEFAULT '{}',
    promoted_from_chat  UUID,      -- chat_graph message_id if promoted
    
    -- Decay
    decay_score     REAL NOT NULL DEFAULT 1.0,
    retention_reason TEXT NOT NULL DEFAULT 'journal_entry',
    
    -- Eviction
    evicted_at      TIMESTAMPTZ,
    eviction_reason TEXT
);

CREATE INDEX IF NOT EXISTS idx_jg_patient_active
    ON ehr.journal_graph (patient_id, created_at DESC)
    WHERE evicted_at IS NULL;

CREATE TABLE IF NOT EXISTS ehr.journal_trend (
    patient_id      TEXT NOT NULL,
    dimension       TEXT NOT NULL CHECK (dimension IN (
        'mood', 'stress', 'sleep', 'pain', 'energy', 'social', 'adherence', 'hope'
    )),
    window_days     INTEGER NOT NULL DEFAULT 30,
    slope           REAL NOT NULL DEFAULT 0.0,
    variance        REAL NOT NULL DEFAULT 0.0,
    current_value   REAL,
    data_points     JSONB NOT NULL DEFAULT '[]',
    last_updated    TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (patient_id, dimension, window_days)
);

COMMENT ON TABLE ehr.journal_graph IS
    'Patient journal graph: psychological state beneath PTV. '
    'Captures mood, stress, sleep, pain, energy, social connection, adherence, and hope. '
    'Decays slower than chat_graph. Connects UP to PTV through anchoring and temporal correlation. '
    'Paying attention is our form of love.';
```

### What This Means for the Product

**For patients:** The app asks "How are you feeling today?" and actually tracks the answer. Not as a disposable chat message that decays in 24 hours. As a dimensional data point that contributes to a trend line that the doctor can see and the detective can reason about. The patient's voice persists.

**For doctors:** A dashboard showing 8 psychological dimensions over time, correlated with clinical events. "Your patient's stress spiked before every documented flare" is actionable clinical intelligence that no lab can provide.

**For EoHD:** The detective gets a complete picture. Clinical timeline + conversational context + psychological state trends. The gap analysis can identify: "Patient reports declining hope and medication non-adherence. Last methotrexate change was 3 weeks ago. Recommend: schedule follow-up to discuss medication tolerability before the next flare window."

**For the business:** This is a moat. Anyone can build FHIR integration. Anyone can build a chat interface. The combination of PTV (clinical timeline) + chat_graph (bounded conversation) + journal_graph (psychological state with trend tracking and PTV correlation) is architecturally novel. It is graph theory applied to the complete patient — body and mind.

---

## Implementation Priority

| Phase | What | Effort |
|-------|------|--------|
| Phase 1 | SQL schema + basic JournalEntry CRUD | 1 day |
| Phase 2 | Heuristic dimension scoring (regex + keyword) | 1 day |
| Phase 3 | LLM dimension refinement (eoh-llama cleanup pass) | 1 day |
| Phase 4 | TrendLine computation + slope/variance | 1 day |
| Phase 5 | EoHD integration (inject trends into detective prompt) | 1 day |
| Phase 6 | Chat promotion (pre-eviction check + journal creation) | 1 day |
| Phase 7 | PTV temporal correlation (connascence entries) | 2 days |
| Phase 8 | Doctor dashboard (React) | 2-3 days |

Total: ~10 working days from schema to dashboard.

---

## The Philosophy

The patient timeline tells you what happened to the body.
The chat graph tells you what was said.
The journal graph tells you how the patient feels about all of it.

PTV is the skeleton. chat_graph is the voice. journal_graph is the heart.

The heart is what makes 2OPMD different from every other health tech company that treats patients as FHIR bundles. We pay attention to things that don't have ICD codes. We track trends in hope. We correlate stress with flares. We notice when someone stops caring.

Paying attention is our form of love. 2OPMD loves its patients.

---

*Filed 2026-04-01. Proposal for journal_graph — psychological state beneath PTV.*

PortalVision maintains state honestly.
