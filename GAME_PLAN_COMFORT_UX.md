# GAME_PLAN_COMFORT_UX.md

**Date:** 2026-04-12  
**Scope:** Frontend polish pass — COMFORT_UX implementation  
**Execution model:** Sequential tasks, each self-contained, each immediately verifiable  
**Companion:** `COMFORT_UX.md` (spec), `READINESS_REPORT.md` (context), `UX_INVARIANTS.md` (constraints)

---

## How to Use This Document

Each task below:
- Targets exactly one or two files
- Describes the before/after state
- Can be verified visually in the browser immediately after the change
- Does not require any subsequent task to be useful

Execute in order. Tasks within the same block are independent if needed, but sequential execution is cleanest.

Dev server: `cd frontend && npm run dev` (serves on port 3000, proxies `/api` to 8000)

---

## Block 0 — CSS Foundations

*Pure CSS and HTML. Zero React component changes. Visible on every page immediately.*

---

### T0.1 — Load Web Fonts

**File:** `frontend/index.html`

**What:** JetBrains Mono and Inter are defined in CSS variables but never loaded. Every user gets system fallback fonts (Courier New on Windows). This is the single highest-ROI change in the entire plan.

**Before:**
```html
<head>
  <meta charset="UTF-8" />
  <link rel="icon" type="image/svg+xml" href="/vite.svg" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>2ndOpinionMD</title>
</head>
```

**After:**
```html
<head>
  <meta charset="UTF-8" />
  <link rel="icon" type="image/svg+xml" href="/vite.svg" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>2ndOpinionMD</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=JetBrains+Mono:ital,wght@0,400;0,500;0,700;1,400&display=swap" rel="stylesheet">
</head>
```

**Verify:** Any monospace text becomes JetBrains Mono. Inter loads for sans-serif labels. The app immediately looks more intentional.

---

### T0.2 — Add Accent Cyan + Animation Keyframes

**File:** `frontend/src/index.css`

**What:** Add the `--accent-cyan` token (used for in-flight/connecting state), define custom animation keyframes (`fade-in`, `blink`), add utility classes for them.

**Add after the existing `:root.light` block:**

```css
/* COMFORT_UX: in-flight/connecting accent */
:root {
  --accent-cyan: #06b6d4;
}

/* COMFORT_UX animation keyframes */
@keyframes fade-in {
  from { opacity: 0; transform: translateY(4px); }
  to   { opacity: 1; transform: translateY(0); }
}

@keyframes blink {
  0%, 100% { opacity: 1; }
  50%       { opacity: 0; }
}

.animate-fade-in {
  animation: fade-in 150ms ease-out forwards;
}

.animate-blink {
  animation: blink 1s step-end infinite;
}
```

**Verify:** No visible change yet — these are utilities. Confirmed working when used in T2.x.

---

### T0.3 — Input Focus Ring

**File:** `frontend/src/index.css`

**What:** All inputs currently show only the browser's default focus indicator. Add a green glow on `:focus-visible` — functional, not decorative (it tells the user which field is active).

**Add after the scrollbar rules at the bottom of `index.css`:**

```css
/* COMFORT_UX: focus ring for all inputs */
input:focus-visible,
textarea:focus-visible,
select:focus-visible {
  outline: none;
  border-color: var(--accent-green) !important;
  box-shadow: 0 0 0 2px rgb(16 185 129 / 0.15);
}
```

**Verify:** Click into any input field (e.g. ASK mode query box). The border turns green and a soft glow appears. The `!important` is necessary because inline `style={{borderColor: ...}}` on the elements would otherwise override this rule.

---

### T0.4 — Body Dot-Grid Background (Optional — Read First)

**File:** `frontend/src/index.css`

**What:** A subtle 24px dot grid on the dark background creates the terminal register without animation. This is the "scanline" effect in COMFORT_UX.md.

> **Note:** COMFORT_UX.md flags this as builder discretion because it uses `radial-gradient`. Skip this task if you want zero gradient policy. Include it if you judge a 1px dot every 24px as structural rather than decorative.

**Add before the scrollbar rules:**

```css
/* COMFORT_UX: terminal dot-grid texture (dark mode only) */
body:not(.light) {
  background-image: radial-gradient(
    circle,
    rgb(55 65 81 / 0.4) 1px,
    transparent 1px
  );
  background-size: 24px 24px;
}
```

**Verify:** Dark background shows a very faint grid of dots at 24px intervals. Should be barely visible — if it's prominent, reduce opacity further (`0.2`).

---

## Block 1 — Global Shell

*Components that appear on every page. Changes here improve every route immediately.*

---

### T1.1 — StatusBar: Pulse During RUNNING

**File:** `frontend/src/components/StatusBar.tsx`

**What:** The status indicator dot is currently static at all times. During RUNNING the dot should pulse to signal live activity. Also: use `--accent-cyan` for the RUNNING state (not yellow — yellow is for warnings; cyan is for in-flight per COMFORT_UX).

**Current `STATUS_STYLES`:**
```ts
const STATUS_STYLES = {
  idle:     { color: 'var(--text-muted)',    label: 'IDLE' },
  running:  { color: 'var(--accent-yellow)', label: 'RUNNING' },
  complete: { color: 'var(--accent-green)',  label: 'COMPLETE' },
  error:    { color: 'var(--accent-red)',    label: 'ERROR' },
};
```

**After:**
```ts
const STATUS_STYLES = {
  idle:     { color: 'var(--text-muted)',   label: 'IDLE',     pulse: false },
  running:  { color: 'var(--accent-cyan)',  label: 'RUNNING',  pulse: true  },
  complete: { color: 'var(--accent-green)', label: 'COMPLETE', pulse: false },
  error:    { color: 'var(--accent-red)',   label: 'ERROR',    pulse: false },
};
```

**Current dot span:**
```tsx
<span
  className="inline-block w-2 h-2 rounded-full"
  style={{ backgroundColor: color }}
/>
```

**After:**
```tsx
<span
  className={`inline-block w-2 h-2 rounded-full ${pulse ? 'animate-pulse' : ''}`}
  style={{ backgroundColor: color }}
/>
```

**Verify:** Submit a query in ASK mode. The status bar dot should breathe/pulse in cyan while the stream is running, then go solid green on completion.

---

### T1.2 — LoadingState: Structured Indicator

**File:** `frontend/src/components/ui/LoadingState.tsx`

**What:** Currently pulses the entire text line. COMFORT_UX pulsing should be on the dot indicator only — the label stays legible.

**Current:**
```tsx
export function LoadingState({ label = 'Loading...' }: LoadingStateProps) {
  return (
    <p className="text-sm font-mono text-[var(--text-muted)] animate-pulse">
      {label}
    </p>
  );
}
```

**After:**
```tsx
export function LoadingState({ label = 'Loading...' }: LoadingStateProps) {
  return (
    <div className="flex items-center gap-2 text-xs font-mono text-[var(--text-muted)]">
      <span
        className="inline-block w-1.5 h-1.5 rounded-full animate-pulse"
        style={{ backgroundColor: 'var(--accent-cyan)' }}
      />
      <span>{label}</span>
    </div>
  );
}
```

**Verify:** Any loading state (Timeline page load, Doctor portal patient list) now shows a breathing cyan dot followed by the label text. The label is stable and readable during load.

---

### T1.3 — Button: Add Transition

**File:** `frontend/src/components/ui/Button.tsx`

**What:** Hover state changes happen instantly. A 150ms color transition makes buttons feel like instruments with physical response.

**Current `BASE`:**
```ts
const BASE = 'rounded font-mono font-bold tracking-wide cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed';
```

**After:**
```ts
const BASE = 'rounded font-mono font-bold tracking-wide cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed transition-colors duration-150';
```

**Verify:** Hover over any Button component. The color change now has a brief fade instead of snapping. Barely perceptible but cumulative effect is polished.

---

### T1.4 — Header: Active Nav Indicator

**File:** `frontend/src/components/Header.tsx`

**What:** Active nav links are colored green, but there's no shape-based indicator. Add an underline on the active link so the current page is clear independent of color.

**Current nav link:**
```tsx
<Link
  key={to}
  to={to}
  className="text-xs font-mono tracking-wide no-underline transition-colors"
  style={{
    color: location.pathname === to
      ? 'var(--accent-green)'
      : 'var(--text-secondary)',
  }}
>
  {label}
</Link>
```

**After:**
```tsx
<Link
  key={to}
  to={to}
  className="text-xs font-mono tracking-wide no-underline transition-colors pb-0.5"
  style={{
    color: location.pathname === to
      ? 'var(--accent-green)'
      : 'var(--text-secondary)',
    borderBottom: location.pathname === to
      ? '1px solid var(--accent-green)'
      : '1px solid transparent',
  }}
>
  {label}
</Link>
```

**Verify:** Navigate between pages. The current page's nav link has a green underline. Other links are visually distinct. Color + shape both indicate active state.

---

## Block 2 — Streaming Core

*The center of the app's UX — what users watch during a query. Maximum visible impact.*

---

### T2.1 — StreamingDisplay: Phase-Specific Status Colors

**File:** `frontend/src/components/StreamingDisplay.tsx`

**What:** All non-error, non-complete states currently render as yellow. Per COMFORT_UX, each phase has a distinct color signal:
- `connecting` → cyan (in-flight)
- `running` → cyan (still in-flight)
- `evidence` → blue (informational — sources retrieved)
- `reasoning` → yellow (advisory — active computation)
- `streaming` → yellow (active)
- `complete` → green (confirmed)
- `error` → red (critical)

**Add a helper function at the top of the component (before the `return`):**

```tsx
function statusColor(s: StreamStatus): string {
  switch (s) {
    case 'connecting':
    case 'running':    return 'var(--accent-cyan)';
    case 'evidence':   return 'var(--accent-blue)';
    case 'reasoning':
    case 'streaming':  return 'var(--accent-yellow)';
    case 'complete':   return 'var(--accent-green)';
    case 'error':      return 'var(--accent-red)';
    default:           return 'var(--text-muted)';
  }
}
```

**Replace the status div (the top colored bar in the render):**

Current:
```tsx
<div
  className={`px-4 py-2 rounded border text-sm font-mono bg-[var(--bg-secondary)] ${
    status === 'error'
      ? 'border-[var(--accent-red)] text-[var(--accent-red)]'
      : status === 'complete'
        ? 'border-[var(--accent-green)] text-[var(--accent-green)]'
        : 'border-[var(--accent-yellow)] text-[var(--accent-yellow)]'
  }`}
>
  {statusText}
</div>
```

After:
```tsx
<div
  className="px-4 py-2 rounded border text-sm font-mono bg-[var(--bg-secondary)] flex items-center gap-2"
  style={{
    borderColor: statusColor(status),
    color: statusColor(status),
  }}
>
  {(status === 'connecting' || status === 'running' || status === 'reasoning' || status === 'streaming') && (
    <span
      className="inline-block w-1.5 h-1.5 rounded-full animate-pulse flex-shrink-0"
      style={{ backgroundColor: statusColor(status) }}
    />
  )}
  {statusText}
</div>
```

**Verify:** Submit a query in ASK mode and watch the status bar cycle:
1. Cyan pulse → "Connecting..."
2. Cyan pulse → "RUNNING"
3. Blue static → "Evidence: N/M sources"
4. Yellow pulse → reasoning step
5. Green static → "Complete — N tokens, Nms"

---

### T2.2 — StreamingDisplay: Fade-In on Answer

**File:** `frontend/src/components/StreamingDisplay.tsx`

**What:** The answer box appears instantly. A 150ms fade-in makes the transition from "no answer" to "answer appearing" feel intentional rather than jarring.

**Current answer block:**
```tsx
{answer && (
  <div
    className="p-4 rounded border prose prose-sm max-w-none bg-[var(--bg-secondary)] border-[var(--border-color)] text-[var(--text-primary)]"
  >
    <Markdown>{answer}</Markdown>
  </div>
)}
```

**After:**
```tsx
{answer && (
  <div className="animate-fade-in">
    <div
      className="p-4 rounded border prose prose-sm max-w-none bg-[var(--bg-secondary)] border-[var(--border-color)] text-[var(--text-primary)]"
    >
      <Markdown>{answer}</Markdown>
    </div>
  </div>
)}
```

**Verify:** Submit a query. When the first token arrives and the answer box appears, it fades in from slightly below rather than snapping into place.

---

### T2.3 — StreamingDisplay: Blink Cursor During Streaming

**File:** `frontend/src/components/StreamingDisplay.tsx`

**What:** While the LLM is streaming tokens, append a blinking cursor character after the answer text. It disappears when streaming completes. Classic terminal feedback.

**Current answer block (after T2.2):**
```tsx
<Markdown>{answer}</Markdown>
```

**After:**
```tsx
<div className="relative">
  <Markdown>{answer}</Markdown>
  {status === 'streaming' && (
    <span
      className="inline-block animate-blink text-[var(--accent-green)] select-none"
      aria-hidden="true"
    >
      ▌
    </span>
  )}
</div>
```

**Verify:** Submit a query. While tokens stream in, a blinking `▌` cursor appears after the last character. It stops blinking and disappears when the stream completes.

> **Note:** The cursor may not visually trail the exact end of markdown-rendered text (markdown renders as HTML). It will appear below the last block element. This is acceptable — it signals activity, not precision position.

---

## Block 3 — Mode Selector

*The first thing users see after login. Currently bare rectangles.*

---

### T3.1 — HomePage: Mode Cards Visual Weight

**File:** `frontend/src/pages/HomePage.tsx`

**What:** Mode cards are plain bordered rectangles. COMFORT_UX target: the cards feel like selectable instruments on a panel. Add a left-border track indicator that activates on hover, and smooth the transition.

**Current button element:**
```tsx
<button
  key={mode.id}
  onClick={...}
  disabled={isAuthenticated && !mode.enabled}
  className="text-left p-6 rounded border transition-colors cursor-pointer disabled:cursor-not-allowed disabled:opacity-50"
  style={{
    backgroundColor: 'var(--bg-secondary)',
    borderColor: 'var(--border-color)',
  }}
  onMouseEnter={(e) => {
    if (mode.enabled || !isAuthenticated) {
      e.currentTarget.style.borderColor = 'var(--accent-green)';
    }
  }}
  onMouseLeave={(e) => {
    e.currentTarget.style.borderColor = 'var(--border-color)';
  }}
>
```

**After (replace the entire button opening tag):**
```tsx
<button
  key={mode.id}
  onClick={...}
  disabled={isAuthenticated && !mode.enabled}
  className="text-left p-6 rounded border-y border-r border-l-[3px] transition-colors duration-150 cursor-pointer disabled:cursor-not-allowed disabled:opacity-50 group"
  style={{
    backgroundColor: 'var(--bg-secondary)',
    borderColor: 'var(--border-color)',
    borderLeftColor: 'transparent',
  }}
  onMouseEnter={(e) => {
    if (mode.enabled || !isAuthenticated) {
      e.currentTarget.style.borderColor = 'var(--border-color)';
      e.currentTarget.style.borderLeftColor = 'var(--accent-green)';
      e.currentTarget.style.backgroundColor = 'var(--bg-tertiary)';
    }
  }}
  onMouseLeave={(e) => {
    e.currentTarget.style.borderColor = 'var(--border-color)';
    e.currentTarget.style.borderLeftColor = 'transparent';
    e.currentTarget.style.backgroundColor = 'var(--bg-secondary)';
  }}
>
```

**Also:** update the mode label inside the card to use a larger weight:

Current label span class: `"text-lg font-mono font-bold tracking-wider"`  
After: `"text-lg font-mono font-bold tracking-widest uppercase"`

**Verify:** Hover over a mode card. The left edge lights up green and the background shifts slightly. Feels like depressing a panel button. The mode labels (ASK, CODING, EoH, EoHD) track with appropriate weight.

---

### T3.2 — HomePage: Description Text Font

**File:** `frontend/src/pages/HomePage.tsx`

**What:** Mode description text is currently `font-mono`. Per COMFORT_UX, descriptions use `font-sans` — it reads more comfortably and creates visual hierarchy between the monospace mode identifier and the sans-serif explanation.

**Current description paragraph:**
```tsx
<p
  className="text-sm"
  style={{ color: 'var(--text-secondary)' }}
>
  {mode.description}
</p>
```

**After:**
```tsx
<p
  className="text-sm font-sans leading-relaxed"
  style={{ color: 'var(--text-secondary)' }}
>
  {mode.description}
</p>
```

**Also:** The subtitle below the 2ndOpinionMD header:
```tsx
<p className="text-sm font-mono" style={{ color: 'var(--text-muted)' }}>
  AI-driven clinical second opinions for autoimmune disease.
</p>
```
Change `font-mono` to `font-sans`.

**Verify:** Mode card descriptions are in Inter (or system sans-serif), readable at a glance. The mode identifier (monospace, bold) and description (sans-serif, normal weight) form a clean visual pair.

---

## Block 4 — Component Tone

*Adjust the emotional register of secondary components — make informational content feel informational, not alarming.*

---

### T4.1 — TransparencyPanel: Calm Default State

**File:** `frontend/src/components/TransparencyPanel.tsx`

**What:** The panel uses `--accent-yellow` for its border and text when a call has been made. Yellow is a warning color. An API call is expected and normal — it should not read as a warning. Only use yellow for genuinely advisory conditions. In resting state, the panel should be quiet.

**Current:**
```tsx
<div
  className="p-3 rounded border text-xs font-mono"
  style={{
    backgroundColor: 'var(--bg-secondary)',
    borderColor: externalCallMade
      ? 'var(--accent-yellow)'
      : 'var(--border-color)',
  }}
>
```

**And the "API call made" span:**
```tsx
<span style={{ color: 'var(--accent-yellow)' }}>
  ⚠ API call made (backend)
  ...
</span>
```

**After:**
```tsx
<div
  className="p-3 rounded border text-xs font-mono"
  style={{
    backgroundColor: 'var(--bg-secondary)',
    borderColor: 'var(--border-color)',
  }}
>
```

```tsx
{externalCallMade ? (
  <span style={{ color: 'var(--text-secondary)' }}>
    ↑ External call — backend
    {callTimestamp && (
      <span style={{ color: 'var(--text-muted)' }}>
        {' '}— {callTimestamp}
      </span>
    )}
  </span>
) : (
  <span>No external calls</span>
)}
```

**Also:** Remove the `⚠` emoji (COMFORT_UX: no emoji). Replace with `↑` (upward arrow — data left the client) which is semantic, not decorative, and passes the emoji rule.

**Verify:** Submit a query in ASK mode. The transparency panel shows the timestamp in muted text without alarm coloring. The information is present without being distracting.

---

### T4.2 — ErrorBoundary: Tone Adjustment

**File:** `frontend/src/components/ErrorBoundary.tsx`

**What:** The error message text currently uses `--accent-red`. The border is already red — that's the signal. The error message body should be `--text-primary` (readable, not shouted). Reserve `--accent-red` for the title and the component stack reference.

**Current cause block:**
```tsx
<p
  className="text-sm font-mono p-3 rounded"
  style={{
    backgroundColor: 'var(--bg-tertiary)',
    color: 'var(--accent-red)',
  }}
>
  {error?.message ?? 'Unknown error'}
</p>
```

**After:**
```tsx
<p
  className="text-sm font-mono p-3 rounded"
  style={{
    backgroundColor: 'var(--bg-tertiary)',
    color: 'var(--text-primary)',
    borderLeft: '2px solid var(--accent-red)',
  }}
>
  {error?.message ?? 'Unknown error'}
</p>
```

**Verify:** Trigger a render error (or temporarily throw in a component). The title `RENDER ERROR` is red. The error message text is white/primary — readable, not blaring.

---

## Block 5 — Typography Sweep

*Audit all pages for `font-mono` on non-data description text. This is a sweep task — hit every page.*

---

### T5.1 — Description Text: font-sans Audit

**Files:** All pages in `frontend/src/pages/`  
**Pattern to find:** `className="text-sm font-mono"` or `className="text-xs font-mono"` on `<p>` tags that contain human-readable description text (not data values, not labels, not status).

**Rule:**
- `font-mono` → keep for: mode names, labels (`CLINICAL QUERY`), status text, data values (timestamps, token counts, source counts, confidence scores, medical codes), navigation links
- `font-sans` → use for: mode descriptions, guidance text, empty state explanations, form helper text, any text that reads as a sentence

**Pages to sweep (check each):**

| Page | What to change |
|------|---------------|
| `AskPage.tsx` | Subtitle "Read-only clinical Q&A. Stateless. SSE streaming." → `font-sans` |
| `CodingPage.tsx` | Any description paragraphs |
| `EohPage.tsx` | Any description paragraphs |
| `EohdPage.tsx` | "Timeline-aware EoH Detective reasoning." → `font-sans`; "Upload your patient timeline PDF..." → `font-sans` |
| `TimelinePage.tsx` | "View event timeline and generate analytics charts." → `font-sans` |
| `JournalPage.tsx` | Description text |
| `SettingsPage.tsx` | Description text |
| `auth/*.tsx` | Helper text under form fields |

**Verify:** Open each page and check that description/guidance text renders in Inter (sans-serif) rather than JetBrains Mono. Code/data values, mode names, and labels remain monospace.

---

## Block 6 — Timeline Track

*The most visually impactful non-trivial change. Replace the flat event list with a proper timeline track component.*

---

### T6.1 — TimelinePage: Vertical Timeline Track

**File:** `frontend/src/pages/TimelinePage.tsx`

**What:** Events are currently reverse-chronological flat cards. Replace with a vertical timeline track — a left border line with event nodes (dots) and event details to the right. Cluster by year/month if there are many events.

**New sub-component to add directly in the file (above `TimelinePage`):**

```tsx
function TimelineTrack({ events }: { events: TimelineEvent[] }) {
  const sorted = [...events].sort(
    (a, b) => new Date(b.ts).getTime() - new Date(a.ts).getTime(),
  );

  const typeColor = (type: string): string => {
    const t = type.toLowerCase();
    if (t.includes('medication') || t.includes('rx')) return 'var(--accent-blue)';
    if (t.includes('lab') || t.includes('result'))    return 'var(--accent-yellow)';
    if (t.includes('diagnosis') || t.includes('dx'))  return 'var(--accent-red)';
    if (t.includes('visit') || t.includes('encounter')) return 'var(--accent-green)';
    return 'var(--text-muted)';
  };

  return (
    <div className="relative pl-6">
      {/* vertical track line */}
      <div
        className="absolute left-2 top-0 bottom-0 w-px"
        style={{ backgroundColor: 'var(--border-color)' }}
      />
      <div className="space-y-3">
        {sorted.map((ev, idx) => (
          <div key={`${ev.ts}-${idx}`} className="relative">
            {/* node dot */}
            <div
              className="absolute -left-[18px] top-1.5 w-2 h-2 rounded-full border"
              style={{
                backgroundColor: 'var(--bg-primary)',
                borderColor: typeColor(ev.event_type),
              }}
            />
            <div
              className="p-3 rounded"
              style={{ backgroundColor: 'var(--bg-tertiary)' }}
            >
              <div className="flex items-start justify-between gap-2 mb-1">
                <span
                  className="text-xs font-mono font-bold"
                  style={{ color: typeColor(ev.event_type) }}
                >
                  {(ev.event_type || 'unknown').toUpperCase()}
                </span>
                <span
                  className="text-xs font-mono flex-shrink-0"
                  style={{ color: 'var(--text-muted)' }}
                >
                  {new Date(ev.ts).toLocaleDateString(undefined, {
                    year: 'numeric', month: 'short', day: 'numeric',
                  })}
                </span>
              </div>
              {ev.text && (
                <p
                  className="text-xs font-sans leading-relaxed"
                  style={{ color: 'var(--text-secondary)' }}
                >
                  {ev.text}
                </p>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
```

**Replace the flat event list render** (the `max-h-80 overflow-y-auto space-y-2` div with individual event cards) with:

```tsx
<div className="max-h-[32rem] overflow-y-auto pr-2">
  <TimelineTrack events={patientTimeline.events} />
</div>
```

**Verify:** Navigate to `/timeline` with a loaded timeline. Events render on a vertical track line. Each event type gets a distinct node color. Events are sorted newest-first.

---

## Block 7 — EoHD Flare Report Polish

*Minor but visible improvements to the most data-dense output in the app.*

---

### T7.1 — EohdPage: Probability Bars

**File:** `frontend/src/pages/EohdPage.tsx`

**What:** The diagnostic landscape bars are 1px tall (`h-1`). They're barely visible. Increase to `h-2` and add the diagnosis name left-aligned with the percentage right-aligned.

**Current bar block:**
```tsx
<div className="w-full h-1 rounded mt-0.5" style={{ backgroundColor: 'var(--bg-tertiary)' }}>
  <div className="h-1 rounded" style={{ width: `${prob * 100}%`, backgroundColor: 'var(--accent-yellow)' }} />
</div>
```

**After:**
```tsx
<div
  className="w-full h-2 rounded mt-1"
  style={{ backgroundColor: 'var(--bg-tertiary)' }}
>
  <div
    className="h-2 rounded transition-all duration-300"
    style={{
      width: `${prob * 100}%`,
      backgroundColor: prob > 0.5 ? 'var(--accent-red)' :
                       prob > 0.25 ? 'var(--accent-yellow)' :
                       'var(--accent-blue)',
    }}
  />
</div>
```

The color tiering (red > 50%, yellow > 25%, blue otherwise) follows clinical risk signaling: high-probability diagnoses read as more urgent.

**Verify:** Generate a flare report in EoHD mode. The probability bars are visible and color-coded by probability weight.

---

### T7.2 — EohdPage: Section Dividers

**File:** `frontend/src/pages/EohdPage.tsx`

**What:** The flare report sections (Precursor Signals, Risk Drivers, Contradictions, Clinician Guidance, Safety Warnings) stack without visual separation. Add a phase-divider line between them.

**Between each major section block inside `{flareReport && (...)}`**, add:

```tsx
<div className="h-px" style={{ backgroundColor: 'var(--border-color)' }} />
```

**Verify:** Flare report sections are visually separated. The output reads as distinct blocks of information rather than a continuous list.

---

## Block 8 — Inline Style Cleanup (Optional Polish Pass)

*This block is style debt. Not required for COMFORT_UX compliance. Do after all other blocks if time permits.*

---

### T8.1 — Replace Inline Styles on Static Values

**Scope:** Any `style={{ color: 'var(--text-muted)' }}` or `style={{ backgroundColor: 'var(--bg-secondary)' }}` that is unconditional (not driven by state) can be replaced with Tailwind utility classes using CSS variable syntax: `text-[var(--text-muted)]`, `bg-[var(--bg-secondary)]`.

**Benefit:** Inline styles have higher specificity and block CSS rules. Converting static ones to classes makes the focus ring (T0.3) and other CSS rules work without `!important`.

**Priority order:**
1. `<input>` and `<textarea>` elements — needed for focus ring to work without `!important`
2. Static label spans and section headers
3. Card backgrounds

**This is a sweep task.** Work through one file at a time. Each file can be a separate commit.

---

## Execution Summary

| Block | Tasks | Est. Time | Impact |
|-------|-------|-----------|--------|
| 0 — CSS Foundations | T0.1–T0.4 | 45 min | **Maximum** — visible everywhere immediately |
| 1 — Global Shell | T1.1–T1.4 | 1 hr | **High** — every page |
| 2 — Streaming Core | T2.1–T2.3 | 1.5 hr | **High** — main interaction loop |
| 3 — Mode Selector | T3.1–T3.2 | 45 min | **High** — first impression |
| 4 — Component Tone | T4.1–T4.2 | 30 min | **Medium** — emotional register |
| 5 — Typography Sweep | T5.1 | 1 hr | **Medium** — cumulative across pages |
| 6 — Timeline Track | T6.1 | 2 hr | **High** — most visual upgrade |
| 7 — EoHD Polish | T7.1–T7.2 | 45 min | **Medium** — data clarity |
| 8 — Inline Cleanup | T8.1 | 2–3 hr | **Low** — style debt |

**Total for B0–B7:** ~8–9 hours of focused work  
**Recommended session order:** Do T0.1 first, always. Everything else benefits from it.

---

## What Is NOT in This Plan

Per UX_INVARIANTS, the following are permanently out of scope:

- Gradient backgrounds on any component
- Slide-in sidebars or drawer navigation
- Toast/notification popups
- Skeleton shimmer animations on text content
- Auto-suggestion or type-ahead in inputs
- Any animation not on this list: `animate-pulse`, `animate-fade-in`, `animate-blink`
- Dark/light theme customization beyond the existing toggle

---

**End of Game Plan**
