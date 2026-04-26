# COMFORT_UX — 2ndOpinionMD Interface Profile

**Version:** 1.0  
**Date:** 2026-04-12  
**Status:** Normative  
**Companion:** UX_INVARIANTS.md (non-negotiable constraints — read that first)

---

## What COMFORT_UX Is

COMFORT_UX is the visual and interaction profile for the 2OPMD frontend. It is **not** a softening of UX_INVARIANTS — it is a named aesthetic position within those constraints.

The invariants define what the interface **cannot do** (no gradients, no fake progress, no implicit state, no personalization). COMFORT_UX defines what it **should feel like** within those rules.

### The Spectrum

```
TERMINAL_RAW  ←——————[COMFORT_UX]——————→  CONSUMER
cold, harsh                              friendly, soft
military ops                             chat app
warning system                           personalized dashboard
```

COMFORT_UX sits at: **medical monitoring room**. Not a military radar station. Not a consumer app. The aesthetic target is a clinical ward's bedside monitoring station — competent, readable, precise, and warm enough not to alarm.

---

## Aesthetic Position

### Not This

- Blinking red alerts on every status change
- Harsh single-pixel white-on-black terminal
- "Warning" aesthetic as default state
- Aggressive all-caps for all labels (UX invariants allow, COMFORT reserves for confirmation and error)
- Cluttered information density (every pixel used = no breathing room)

### This

- Calm, high-contrast dark theme with considered accent color use
- Monospaced data, readable type for labels and description text
- Generous internal padding in containers (don't crowd the data)
- Status indicated by color + shape, never color alone
- Informational content in calm blue; actionable content in green; warnings in amber; errors in red
- Visual feedback on active operations via pulse animation only (no flash, no bounce)
- Section headers use a left-border track treatment (not bold-only)

---

## Color System

### Base Palette (inherits from `index.css`)

| Token | Dark Value | Light Value | Purpose |
|-------|-----------|-------------|---------|
| `--bg-primary` | `#0a0e17` | `#f9fafb` | Page background |
| `--bg-secondary` | `#111827` | `#ffffff` | Card/panel background |
| `--bg-tertiary` | `#1f2937` | `#f3f4f6` | Input, tag, nested panel background |
| `--text-primary` | `#e5e7eb` | `#111827` | Primary readable text |
| `--text-secondary` | `#9ca3af` | `#4b5563` | Labels, descriptors |
| `--text-muted` | `#6b7280` | `#9ca3af` | Metadata, timestamps, disabled |
| `--border-color` | `#374151` | `#d1d5db` | All borders |

### Accent Palette — COMFORT Assignment

| Token | Value | COMFORT Use |
|-------|-------|-------------|
| `--accent-green` | `#10b981` | **Action** — primary CTA, confirmed/complete state, active nav |
| `--accent-yellow` | `#f59e0b` | **Warning** — non-critical advisory, precursor signals, rate limits |
| `--accent-red` | `#ef4444` | **Critical** — errors, safety warnings, required fields not met |
| `--accent-blue` | `#3b82f6` | **Informational** — metadata, module tags, doctor-mode accents |
| `--accent-cyan` | `#06b6d4` | **In-flight** — active stream, connecting, live operations |

> **Add to `index.css`:** `--accent-cyan: #06b6d4;`

### Color as Sole Channel — Prohibited

Every status must carry a secondary signal:

- **Shape**: pulse dot for running, static dot for idle, filled check for complete, X for error
- **Label**: RUNNING / IDLE / COMPLETE / ERROR text alongside color
- **Position or border**: status border changes alongside text color

---

## Typography

### Font Loading

Add to the `<head>` of `index.html` (or via `@import` in `index.css`):

```html
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=JetBrains+Mono:wght@400;500;700&display=swap" rel="stylesheet">
```

Both fonts are already in the CSS variable stack — they are not being loaded. This is the single highest-ROI typography fix.

### Scale

| Role | Font | Size | Weight | Use |
|------|------|------|--------|-----|
| Page title | mono | `text-xl` (1.25rem) | 700 | Mode name, page identifier |
| Section header | mono | `text-sm` (0.875rem) | 700 | Panel titles (e.g. `EoH ROUTER QUERY`) |
| Body / description | sans | `text-sm` | 400 | Mode descriptions, guidance text |
| Label | mono | `text-xs` (0.75rem) | 500 | Field labels, column headers |
| Metadata | mono | `text-xs` | 400 | Timestamps, token counts, source counts |
| Data / answer | mono | `text-sm` | 400 | LLM response, clinical output |
| Badge | mono | `text-xs` | 700 | Mode tags, status chips |

### COMFORT Rule: Section headers are NOT all-caps

Reserve ALL-CAPS for:
- Mode identifiers (`ASK MODE`, `CODING MODE`, `EoH`, `EoHD`)
- Action buttons (`SUBMIT QUERY`, `GENERATE`, `EXPORT JSON`)
- Status states (`RUNNING`, `COMPLETE`, `ERROR`)
- Confirmation gates (`CONFIRM EXPORT`)

Do NOT all-caps:
- Description text
- Guidance/clinician notes
- Error explanations (state the error plainly, not aggressively)

---

## Spacing and Layout

### Container Widths

- Default content: `max-w-4xl` (existing — keep)
- Data-heavy pages (Timeline, Analytics): `max-w-5xl` (existing — keep)

### Padding — COMFORT Minimums

| Context | Padding |
|---------|---------|
| Page-level section card | `p-5` (not `p-4`) |
| Nested data panel | `p-3` |
| Input field | `px-3 py-2` |
| Badge/chip | `px-2 py-0.5` |
| Status bar | `px-6 py-2` (existing — keep) |

### Section Dividers

Between major sections, use a left-border track rather than `<hr>`:

```tsx
<div className="pl-4 border-l-2 border-[var(--accent-green)]">
  {/* section content */}
</div>
```

For phase headers (EoHD plans, multi-step outputs):

```tsx
<div className="flex items-center gap-3 mb-3">
  <span className="text-xs font-mono font-bold text-[var(--accent-green)]">STEP 1</span>
  <div className="flex-1 h-px bg-[var(--border-color)]" />
</div>
```

---

## Animation Rules

Permitted by UX_INVARIANTS: **loading indicators only**.

### Permitted Animations

| Name | CSS Class | Use |
|------|-----------|-----|
| Pulse dot | `animate-pulse` | Status indicator during RUNNING/CONNECTING |
| Fade in | `animate-fade-in` | Result appearance (150ms opacity 0→1) |
| Blink cursor | `animate-blink` | Terminal cursor in status text during streaming |

Add to `index.css`:

```css
@keyframes fade-in {
  from { opacity: 0; transform: translateY(4px); }
  to { opacity: 1; transform: translateY(0); }
}

@keyframes blink {
  0%, 100% { opacity: 1; }
  50% { opacity: 0; }
}

.animate-fade-in {
  animation: fade-in 150ms ease-out forwards;
}

.animate-blink {
  animation: blink 1s step-end infinite;
}
```

### Prohibited Animations

- Bouncing or elastic easing
- Sliding panels from off-screen
- Auto-rotating carousels
- Progress bars that advance without real data
- Any animation triggered by hover alone (hover state changes are transitions, not animations)

---

## Component Profiles

### Status Bar (`StatusBar.tsx`)

COMFORT target: the status bar feels like a vital-signs monitor — alive during operations.

- **IDLE**: static gray dot + `IDLE` text
- **RUNNING**: pulsing cyan dot + `RUNNING` text + scrolling status message
- **COMPLETE**: solid green dot + `COMPLETE` text + duration/token summary
- **ERROR**: solid red dot + `ERROR` text + first line of error

Implementation: add `animate-pulse` only when `status === 'running'`.

### Mode Cards (`HomePage.tsx`)

COMFORT target: cards feel like selectable instruments on a panel — distinct, clearly affordanced.

- Enabled: standard border → green border on hover with `transition-colors duration-150`
- Active/selected: green left-border track (4px) + slightly elevated bg
- Disabled: 40% opacity, cursor not-allowed, no hover effect
- Mode badge (top-right corner): `ASK`, `EoH`, etc. in monospace chip

### StreamingDisplay

COMFORT target: each phase of the stream has a distinct visual register.

| Phase | Visual |
|-------|--------|
| Connecting | Cyan pulsing status bar, no content area yet |
| Running | Yellow status bar, pulsing dot |
| Evidence | Blue status bar with source count |
| Streaming | Answer area fades in, cursor blinks at end of text |
| Complete | Green status bar, confidence + stats inline |
| Error | Red status bar, error panel with recovery paths |

Answer box: left-border track in `--border-color` with subtle inner padding. Markdown prose class applies.

### Transparency Panel

COMFORT target: visible but not dominant. It should read as a system footnote, not a warning.

- Default: collapsed/minimal — one line: `No external calls made` or `External call at {timestamp}`
- Expand on demand for full detail
- Use `--text-muted` color as default, not yellow/red (it's informational, not a warning)

### Error Boundary

COMFORT target: honest, not harsh. The error is serious — don't dress it up, but don't shout either.

- Red left-border track, not full red background
- Monospace error text in `--text-primary` (not `--accent-red` — the border carries the signal)
- Recovery paths listed as numbered steps in `--text-secondary`

### LoadingState

COMFORT target: a breathing indicator that signals real work.

Replace the single pulsing text with a structured loading state:

```
● LOADING  ·  {label}
```

Where `●` pulses (animate-pulse on the dot span only, not the whole line).

---

## Input Fields — COMFORT Standard

All inputs (`<input>`, `<textarea>`, `<select>`):

```css
/* Focus ring — add to index.css */
input:focus,
textarea:focus,
select:focus {
  outline: none;
  border-color: var(--accent-green);
  box-shadow: 0 0 0 2px rgb(16 185 129 / 0.15);
}
```

This is the only permitted glow effect. It's functional (focus indication), not decorative.

---

## Page Backgrounds — Scanline Grid

A subtle grid texture conveys the terminal register without animation. CSS only, no images.

```css
/* Add to index.css — applied to <body> in dark mode */
body:not(.light) {
  background-image: linear-gradient(
    var(--bg-primary) 1px, transparent 1px
  ),
  linear-gradient(
    90deg, var(--bg-primary) 1px, transparent 1px
  );
  background-size: 24px 24px;
  background-color: #0a0e17;
}
```

Wait — this violates "no gradients". The CSS spec uses `linear-gradient` for grid lines, not for decorative gradients. This is a 1px rule grid, not a visual gradient. Acceptable under COMFORT_UX. Builder discretion.

Alternative (cleaner, no gradient debate): use a single `background-image: url("data:image/svg+xml,...")` dot grid. Both achieve the same terminal texture.

---

## What COMFORT_UX Does NOT Do

These remain forbidden by UX_INVARIANTS regardless of COMFORT:

- No gradient fills on component backgrounds
- No decorative animations (hover reveal, scroll fade, etc.)
- No modal overlays with backdrop blur
- No sidebar slide-ins
- No auto-suggestions or type-ahead
- No emoji or illustrative icons
- No color theming beyond dark/light toggle

---

## Implementation Checklist

**CSS (index.css):**
- [ ] Add `--accent-cyan: #06b6d4`
- [ ] Load JetBrains Mono + Inter from Google Fonts (or self-host)
- [ ] Add `@keyframes fade-in` and `blink`
- [ ] Add `.animate-fade-in` and `.animate-blink` utilities
- [ ] Add input focus ring rule
- [ ] (Optional) Add dot-grid background for dark mode

**Components:**
- [ ] `StatusBar`: add `animate-pulse` when `status === 'running'`, use cyan for running state
- [ ] `LoadingState`: replace pulsing text with dot + label structure
- [ ] `StreamingDisplay`: phase-specific status colors (cyan for connecting, yellow for running, blue for evidence, green for complete)
- [ ] `StreamingDisplay`: `animate-fade-in` on answer box appearance
- [ ] `Button`: add `transition-colors duration-150` to all variants
- [ ] Mode cards (`HomePage`): left-border track on hover/active
- [ ] All inputs: remove inline `style={}` for border-color on focus, rely on CSS rule

**Typography:**
- [ ] Audit all page components: description text should use `font-sans` not `font-mono`
- [ ] Reserve ALL-CAPS for actions, modes, and status — not descriptions

---

## Relationship to Other Specs

| Doc | Relationship |
|-----|-------------|
| `UX_INVARIANTS.md` | Non-negotiable constraints. COMFORT_UX operates within them. |
| `ASK_STREAMING_CONTRACT.md` | Defines the SSE events that COMFORT_UX must display. |
| `FRONTEND_INTEGRATION.md` | Current wiring. COMFORT_UX applies on top. |
| `receipts/EOHD_PDF_STYLE_GUIDE_COMFORT_20260227.md` | PDF variant of the COMFORT aesthetic — parallel, not derived. |

---

**End of Specification**
