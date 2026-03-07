# 2OPMD -- Figma Page Structure + Components Checklist

**Date:** 2026-03-07
**From:** Dylan (via updated spec, mid-run)
**For:** Devin, Nate, Design
**Purpose:** Canonical Figma page structure, full components checklist, screen checklists, motion rules, copy system, and build order for the 2OPMD React Native mobile prototype.

---

## North Star

Build 2OPMD as a premium chronic-illness timeline engine that feels:
- as easy as Daylio
- as useful daily as Visible
- as comprehensive as Guava and Bearable
- as emotionally legitimate as How We Feel
- as visually trustworthy as Apple Health

It must not feel like:
- a symptom tracker junk drawer
- a wellness app
- a mood app
- a dashboard swamp
- a chatbot wrapper

---

## What We Are Borrowing From Each App

### How We Feel

**Keep:**
- nuanced emotion selection
- elegant bubble interaction
- science-backed emotional legitimacy
- dark, cinematic emotional check-in references only for concept stage

**Do not copy:**
- therapy-first product framing
- regulation tools as the core product

### Bearable

**Keep:**
- breadth of data categories
- modular check-in structure
- delayed paywall / value-first approach
- customizable tracking dimensions

**Do not copy:**
- onboarding sprawl
- cute mascot energy
- cluttered active home
- too many simultaneous cards and toggles

### Guava

**Keep:**
- chronic-care seriousness
- provider / records integration framing
- medical profile and conditions structure
- "whole picture" credibility

**Do not copy:**
- operational heaviness too early
- account / connection work before value is felt

### Daylio

**Keep:**
- low-friction input
- visual satisfaction of quick selections
- the feeling that logging is tiny and repeatable

**Do not copy:**
- wellness softness
- generic self-help tone
- emoji-first identity

### Apple Health

**Keep:**
- visual hierarchy
- summary-first layout
- trust copy style
- clean cards with lots of whitespace
- trend surfaces that feel calm and authoritative

**Do not copy:**
- generic broadness
- passive "just browse data" product posture

---

## Figma File Page Structure

### 00 -- Cover + Product Truth

Use this page as the anchor.

Include:
- product one-liner
- target audiences
- brand lines
- north-star screenshots
- design commandments

Frames:
- 00.1 Product Definition
- 00.2 Audience
- 00.3 Brand Lines
- 00.4 Design Commandments
- 00.5 Competitive Synthesis Snapshot

### 01 -- Inspiration Audit

This page is for screenshot references only.
Organize by source app and annotate what to steal / reject.

Sections:
- How We Feel
- Bearable Onboarding
- Bearable Activated Experience
- Guava Onboarding
- Guava Active / Features
- Daylio
- Apple Health

For each source, add 3 labels:
- Steal
- Avoid
- Translate for 2OPMD

### 02 -- Brand + Tokens

This is the source of visual truth.

Sections:
- Color palette
- Type scale
- Spacing scale
- Radius system
- Shadows
- Icon rules
- Motion rules
- Severity color system

Core tokens:
- Background / Surface / Elevated Surface
- Primary text / Secondary text / Tertiary text
- Accent green
- Mild / Moderate / Severe / Flare
- Success / Warning / Error / Info

### 03 -- Foundations

Reusable design primitives.

Include:
- App shell
- Safe areas
- Top navigation patterns
- Bottom navigation patterns
- Grid / spacing system
- Card spacing rules
- Input spacing rules
- Divider rules
- Empty state rules
- Microcopy rules

### 04 -- Components

Every reusable component lives here.
Everything in screens must be built from these.

Subpages / sections:
- Buttons
- Inputs
- Selectors
- Chips / tags
- Cards
- Navigation
- Charts / timelines
- Calendar cells
- Tree module
- Modals / sheets
- Feedback / alerts
- Upload components
- Skeletons / loading

### 05 -- Onboarding Flow

Only onboarding screens.
Each screen should be a clean mobile frame with notes.

### 06 -- Core Home + Daily Loop

Home, quick check-in, emotional context, structured journal.

### 07 -- Analysis + Visit Prep

Patterns emerging, advanced analysis, prepare-for-visit, timeline views.

### 08 -- Monetization + Upgrades

Day 3 first-pattern moment, free trial modal, premium comparison, continue basic mode.

### 09 -- States + Edge Cases

Loading, empty, partial, offline, upload failure, no pattern yet, not enough data, disconnected record source, etc.

### 10 -- Prototype Paths

Clickable prototype flows for:
- consumer demo
- investor demo
- diagnosed user flow
- searching user flow
- Day 3 "first pattern" flow

### 11 -- Dev Handoff

Annotated redlines, spacing references, interaction notes, component mapping, fake data examples.

---

## Components Checklist

### A. Navigation

- [ ] Top app bar -- centered title
- [ ] Top app bar -- back + title
- [ ] Top app bar -- back + progress
- [ ] Bottom nav -- 3 tab version
- [ ] Bottom nav -- 4 tab version
- [ ] Floating primary CTA bar (only where needed)

### B. Buttons

- [ ] Primary button -- default / pressed / disabled / loading
- [ ] Secondary button -- outline
- [ ] Tertiary text button
- [ ] Icon button -- small
- [ ] Icon button -- circular
- [ ] Inline link button

### C. Inputs

- [ ] Single-line text field
- [ ] Search field
- [ ] Multiline note field
- [ ] Email field
- [ ] OTP / code input
- [ ] Date picker trigger
- [ ] Dropdown / select

### D. Selection Controls

- [ ] Radio card selector
- [ ] Checkbox row
- [ ] Toggle switch
- [ ] Pill selector
- [ ] Tag chips
- [ ] Emotion bubble selector
- [ ] Severity hold state selector

### E. Cards

- [ ] Intro / explanation card
- [ ] Metric summary card
- [ ] Pattern insight card
- [ ] Next step card
- [ ] Trust / privacy card
- [ ] Record upload card
- [ ] Clinician summary card
- [ ] Premium feature card

### F. Calendar + Timeline

- [ ] 30-day map container
- [ ] Calendar day -- empty
- [ ] Calendar day -- bad day
- [ ] Calendar day -- mild
- [ ] Calendar day -- moderate
- [ ] Calendar day -- severe
- [ ] Calendar day -- flare
- [ ] Legend row
- [ ] Timeline preview row
- [ ] Timeline event card

### G. Tree System

- [ ] Oak tree idle state
- [ ] Oak tree watered state
- [ ] Oak tree growth states
- [ ] Streak counter badge
- [ ] Signal strengthening label

### H. Check-in System

- [ ] 0-10 physical slider
- [ ] Quick toggles row
- [ ] Emotional bubble field
- [ ] Journal section header
- [ ] Journal completion footer
- [ ] Save confirmation micro-toast

### I. Journal Modules

- [ ] Symptom shift module
- [ ] Trigger selection module
- [ ] Context note module
- [ ] Environment / behavior module
- [ ] Optional add-photo / file attachment trigger

### J. Analysis Modules

- [ ] Consistency meter
- [ ] Pattern clarity meter
- [ ] Confidence meter
- [ ] Evidence summary block
- [ ] What changed block
- [ ] What improves accuracy block
- [ ] Questions to ask block

### K. Upload / Records

- [ ] Upload PDF card
- [ ] Upload image card
- [ ] Portal connect card
- [ ] File processing state
- [ ] Parsed results preview
- [ ] Upload error state

### L. Monetization

- [ ] First pattern modal
- [ ] Trial offer card
- [ ] Premium features comparison
- [ ] Continue with basic mode button
- [ ] Reminder before trial ends explainer

### M. Feedback States

- [ ] Empty state
- [ ] Not enough data yet state
- [ ] Partial data state
- [ ] Loading skeleton
- [ ] Error state
- [ ] Success state

---

## Screen Checklist -- Onboarding

### O1 -- Splash

**Purpose:** create premium first impression

**Elements:**
- off-white background
- centered Great Oak symbol
- no text
- subtle heartbeat / pulse motion

### O2 -- Welcome

**Purpose:** instantly call out the ICP

**Elements:**
- small oak mark top center
- headline
- subhead
- primary CTA
- secondary login link
- micro trust line

**Copy direction:**
- "Chronic symptoms deserve clarity."
- "For autoimmune, chronic illness, and anyone still searching for answers."

### O3 -- Promise

**Purpose:** show what happens when they use it

**Elements:**
- 3 compact cards
- one-line subhead
- continue CTA
- how-it-works link

### O4 -- Credibility

**Purpose:** establish that this is more than a tracker

**Elements:**
- headline
- 2 proof tiles
- optional learn-more link

### O5 -- Name

**Elements:**
- text field
- continue

### O6 -- Age

**Elements:**
- age range cards / radio rows
- continue

### O7 -- Gender Identity

**Elements:**
- female / male / another identity / prefer not to say
- text input shown only if "another identity" selected

### O8 -- Diagnosed vs Searching

**Elements:**
- two large cards
- one CTA
- minimal explanatory copy

### O9A -- Diagnosed Path

**Elements:**
- searchable diagnosis field
- quick chips
- credibility through breadth

### O9B -- Searching Path

**Elements:**
- short text explanation field
- helper text with example

### O10 -- 30-Day Bad-Day Map

**Purpose:** serious interaction that creates immediate signal

**Elements:**
- month grid
- severity legend
- "estimate is fine" helper copy
- counters
- continue CTA

### O11 -- Emotional Context

**Purpose:** capture mental / emotional signal as context

**Elements:**
- bubble selection field
- choose up to 5
- clinical framing copy

### O12 -- Top Symptoms

**Elements:**
- search
- chips
- selected state

### O13 -- Journaling Value

**Purpose:** explain why journaling matters

**Elements:**
- headline
- 3 bullet cards
- continue CTA
- example summary link optional

### O14 -- 3-Day Baseline Commitment

**Elements:**
- short mission card
- "Start 3-day baseline" CTA

### O15 -- Save Progress

**Elements:**
- Apple / Google / Email options
- privacy line

### O16 -- Optional Records

**Elements:**
- upload PDF
- upload image
- skip for now

### O17 -- Starting Snapshot

**Elements:**
- what we know
- what we'll watch
- what improves accuracy
- go to home CTA

---

## Screen Checklist -- Core Product

### H1 -- Home

**Elements:**
- tree + streak
- today check-in card
- patterns emerging card
- next step card
- collapsed timeline preview
- advanced analysis CTA
- prepare for visit CTA

### H2 -- 2-Second Check-In

**Elements:**
- physical slider
- optional toggles
- save CTA

### H3 -- Emotional Check-In

**Elements:**
- bubble field
- quick save

### H4 -- Structured Journal

**Elements:**
- 4 modules
- optional attachments
- completion CTA

### H5 -- Journal Confirmation

**Elements:**
- subtle success state
- watered tree animation
- one-line intelligent acknowledgement

### H6 -- Patterns Emerging

**Elements:**
- one-sentence insight
- not-enough-data variant
- confidence / clarity hints

### H7 -- Advanced Analysis

**Elements:**
- consistency
- pattern clarity
- confidence
- evidence summary
- what changed
- what improves accuracy
- what to ask next

### H8 -- Prepare for Visit

**Elements:**
- summary card preview
- timeline snapshot
- top patterns
- recent changes
- questions to ask
- export CTA

### H9 -- Timeline Detail

**Elements:**
- event rows
- pattern markers
- symptom spikes
- context chips

### H10 -- Records / Upload Center

**Elements:**
- uploaded docs list
- processing states
- parsed preview
- connect provider entry point

---

## Monetization Checklist

### M1 -- Day 3 First Pattern Moment

**Elements:**
- headline: first pattern detected
- one meaningful insight
- see more CTA

### M2 -- Premium Offer

**Elements:**
- 7-day free trial positioning
- deeper analysis benefits
- clinician export benefits
- longer horizon benefits
- continue with basic mode

### Monetization Rules

- do not paywall onboarding
- do not ask for money before first value
- do not use gimmicky urgency
- keep tone premium, clinical, calm

---

## Motion Checklist

Motion must be subtle and premium.

**Include:**
- splash pulse
- button press depth
- card entrance fade / rise
- tree watering micro-animation
- bubble selection animation
- severity hold feedback on calendar
- save confirmation toast fade
- smooth modal sheet transitions

**Avoid:**
- flashy gradient motion
- gamified confetti
- excessive bounce
- cute personality animations

---

## Copy System Rules

**Use:**
- calm
- sharp
- brief
- clinically serious
- emotionally safe

**Avoid:**
- hype
- startup jargon
- wellness fluff
- over-explaining
- therapy-app softness

**Good examples:**
- "Patterns emerging."
- "We're watching whether sleep aligns with symptom spikes."
- "Signal strengthens with consistency."
- "Built to support your clinician conversation."
- "Not enough data yet."

**Bad examples:**
- "You're doing amazing sweetie!"
- "Unlock your best self."
- "AI-powered holistic wellness revolution."

---

## Non-Negotiables

1. The app must feel premium.
2. The app must feel medically serious.
3. The daily loop must be tiny.
4. Journaling must feel useful, not decorative.
5. Emotional context must feel legitimate, not fluffy.
6. Home must stay minimal.
7. The tree must represent consistency only.
8. "Prepare for visit" must remain central.
9. Trust language must be plainspoken.
10. Value must come before monetization.

---

## Build Order Recommendation

### Phase 1 -- Foundations
- tokens
- typography
- spacing
- shell
- buttons
- cards
- selectors
- nav

### Phase 2 -- Onboarding
- O1 to O17

### Phase 3 -- Core Loop
- H1 to H5

### Phase 4 -- Analysis + Visit Prep
- H6 to H10

### Phase 5 -- Monetization + States
- M1 / M2
- empty / error / partial / loading states

---

## Final Design Brief

Build 2OPMD as the most elegant chronic illness timeline engine on mobile:
- serious enough for hard cases
- light enough to use daily
- beautiful enough to trust
- useful enough to change the appointment
