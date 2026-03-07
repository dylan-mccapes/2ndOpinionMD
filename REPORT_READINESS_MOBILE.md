# REPORT_READINESS_MOBILE

**Date:** 2026-03-07
**From:** Devin (Cognition)
**To:** Dylan, Nate
**Status:** Ready for tasking

---

## SOURCES INGESTED

| Document | Location | Summary |
|---|---|---|
| Mobile SpellBook | `2opmd_mobile_spellbook.json` | 251-line manifest: React Native prototype spec for investor demo. Covers project scope, architecture (Expo, React Navigation, Zustand/Context, fetch-only HTTP, expo-secure-store for JWT), full API endpoint map (auth, journal, RAG streaming, timeline, utility), screen definitions (Login, Today, Journal, Timeline, Ask, Settings), user flows (daily loop, journal entry, ask question), component specs (TodayCheckIn, JournalList, JournalEditor, TimelineView, AskInput, StreamingAnswer, ErrorDisplay), UX invariants (no optimistic UI, honest failures, offline handling), aesthetic (dark-first, clinical, clean), style guide summary with color tokens and typography, Devin build instructions with 9-step priority order, constraints, and testing commands. |
| Handoff | `HANDOFF_DEVIN_MOBILE.md` | Context transfer from Dylan to Devin. Defines the first task: create this readiness report before build. Specifies required sections, key caveats (style guide = reference only, design commandments = not yet canonical, spellbook + prototype_scope_nate = build authority), and post-report workflow (treat report as execution checklist, build in phase order, file receipts). |
| Prototype Scope (Nate) | `2opmd_mobile_spellbook.json` → `prototype_scope_nate` | Must-have modules: onboarding (8 screens: diagnosed vs searching fork, 30-day bad-day map, emotion context, symptoms selection, journaling value, save account, optional upload, starting snapshot), home (4 features: 2-second daily check-in, structured journal, patterns emerging card, advanced analysis), other (3 features: prepare for visit, Day 3 first-pattern moment, premium upsell modal). Mockable: real backend logic, inference engine, records parsing, prediction math, clinician PDF generation. Constraint: prototype should feel real. |
| Style Guide | `mobile_spec/STYLE_GUIDE.md` | 170-line style reference derived from How We Feel app. **Style reference only — images are from a different app.** Dark mode first (#000000 bg). Color palette: 13 tokens (bg, text, accent, emotion families). Typography: serif headlines (Georgia/Lora/Playfair, 28-34pt), sans-serif body (SF Pro/Inter/Roboto, 16-18pt). Components: pill-shaped white buttons (52px min height), emotion bubbles (circular, color-coded, organic cluster), thin white progress indicator, black bottom nav with outline icons. Layout: 20-24px horizontal padding, 24-32px section spacing. Image manifest maps 25+ reference screenshots to screens. |
| Design Commandments | `mobile_spec/2opmd_design_commandments.md` | 584-line design north star from Nate. **Not yet canonical — Dylan reviewing.** Core identity: "Not a journal. Not a chatbot. A timeline engine." 15 commandments covering: audience specificity (autoimmune/chronic illness), value before setup, 30-day bad-day map as flagship interaction, emotional context (valid but not central), structured 4-part journal, tiny daily loop (10s basic, 30-60s full), signal-building feedback, radically simple home, Tree of Life (rewards consistency not health status), plainspoken trust, prepare-for-visit as holy-shit feature, premium after value, competitive positioning (Guava, Visible, Bearable, Daylio, How We Feel, Apple Health). v1 must-haves and nice-to-haves defined. |
| Spellbook Spec Report | `reports/REPORT_MOBILE_SPELLBOOK_SPEC_20260306.md` | **Not yet present in repo.** Referenced in handoff as gaps and recommendations analysis. Will need to be created or ingested when available. |
| Parent SpellBook | `2opmd_spellbook.json` | 440-line parent manifest for 2OPMD web platform. Shared backend (FastAPI at `server/api/app_postgres.py`), shared API contracts (auth, journal, RAG streaming, timeline, EoH, terminologies, guidelines, genomics, utility — 100+ endpoints), UX invariants (9 hard rules), aesthetic spec (clinical terminal), environment config, Make targets, Docker setup, security model (JWT, rate limits, email verification), Devin constraints. Mobile inherits backend and API contracts from this spec. |
| Figma Page Structure + Components | `mobile_spec/FIGMA_PAGE_STRUCTURE_COMPONENTS.md` | Updated mid-run spec from Dylan. Canonical Figma page structure (00-11: Cover, Inspiration Audit, Brand+Tokens, Foundations, Components, Onboarding, Core Home, Analysis+Visit Prep, Monetization, States+Edge Cases, Prototype Paths, Dev Handoff). Full components checklist (13 categories: Navigation, Buttons, Inputs, Selection Controls, Cards, Calendar+Timeline, Tree System, Check-in System, Journal Modules, Analysis Modules, Upload/Records, Monetization, Feedback States). Screen checklists: 17 onboarding screens (O1-O17, expanded from original 8 with Splash, Welcome, Promise, Credibility, Name, Age, Gender Identity, 3-Day Baseline Commitment), 10 core product screens (H1-H10), 2 monetization screens (M1-M2). Motion checklist, copy system rules, non-negotiables (10 items), build order (5 phases: Foundations, Onboarding, Core Loop, Analysis+Visit Prep, Monetization+States). Competitive synthesis: what to steal/avoid from How We Feel, Bearable, Guava, Daylio, Apple Health. |
| Figma | [2opmd.app.figma](https://www.figma.com/design/ek23oisUl8U91A5WW3oo7m/2opmd.app.figma?node-id=0-1&p=f) | Compiled screenshots from Nate. Devin can reference for visual direction. |

---

## TASK LIST (Execution Order)

### Phase 1: Read / Ingest

| # | Task | Routing (Where to Find Everything) |
|---|---|---|
| 1.1 | **Read parent spellbook** | `2opmd_spellbook.json` — shared backend, same API contracts. All endpoints at `api_endpoints`. UX invariants at `ux_invariants.hard_rules[]`. Environment at `environment`. |
| 1.2 | **Read mobile spellbook** | `2opmd_mobile_spellbook.json` — full mobile build spec. `prototype_scope_nate` (must-have modules, mockable items). `stack` (React Native, Expo, React Navigation, Zustand/Context, fetch, expo-secure-store). `api_endpoints` (auth, journal, RAG streaming, timeline, utility). `screens`, `flows`, `components`. |
| 1.3 | **Read prototype scope** | `2opmd_mobile_spellbook.json` → `prototype_scope_nate` — must-have modules (onboarding, home, other), mockable backend items, "whole story simply" principle. |
| 1.4 | **Read style guide (reference only)** | `mobile_spec/STYLE_GUIDE.md` — colors, typography, component shapes, layout. Images from How We Feel — do NOT build those screens. Apply visual language to 2OPMD flows. Image manifest at section 8. |
| 1.5 | **Read design commandments (background only)** | `mobile_spec/2opmd_design_commandments.md` — Nate's design north star, not yet canonical. Use as design intent. Spellbook + prototype_scope_nate are build authority. |
| 1.6 | **Read spellbook spec report** | `reports/REPORT_MOBILE_SPELLBOOK_SPEC_20260306.md` — gaps and recommendations. **Not yet in repo; ingest when available.** |
| 1.7 | **Read this handoff** | `HANDOFF_DEVIN_MOBILE.md` — task definition, caveats, post-report workflow. |
| 1.8 | **Read Figma page structure + components checklist** | `mobile_spec/FIGMA_PAGE_STRUCTURE_COMPONENTS.md` — updated mid-run spec from Dylan. Canonical Figma page structure (pages 00-11), full components checklist (13 categories, 80+ components), expanded screen checklists (O1-O17 onboarding, H1-H10 core, M1-M2 monetization), motion rules, copy system, non-negotiables, build order. **This doc expands the onboarding from 8 screens to 17** (adds Splash, Welcome, Promise, Credibility, Name, Age, Gender Identity, 3-Day Baseline Commitment). Build authority alongside spellbook + prototype_scope_nate. |

### Phase 2: Scaffold React Native (Expo) + Foundations

| # | Task | Routing (Where to Find Everything) |
|---|---|---|
| 2.1 | **Init Expo project** | `2opmd_mobile_spellbook.json` → `stack.recommended.cli`: "Expo (easiest) or react-native init". Use Expo for speed. |
| 2.2 | **Install navigation** | `2opmd_mobile_spellbook.json` → `stack.recommended.navigation`: React Navigation (stack + tab). |
| 2.3 | **Install state management** | `2opmd_mobile_spellbook.json` → `stack.recommended.state`: React Context or Zustand — minimal. |
| 2.4 | **Install secure storage** | `2opmd_mobile_spellbook.json` → `stack.recommended.secure_storage`: expo-secure-store (JWT storage). |
| 2.5 | **Install SSE support** | `2opmd_mobile_spellbook.json` → `stack.sse_note`: "React Native has no native EventSource. Use react-native-sse or polyfill with fetch + stream parsing." |
| 2.6 | **Configure environment** | `2opmd_mobile_spellbook.json` → `environment`: `EXPO_PUBLIC_API_BASE` or `API_BASE_URL` = `http://localhost:8000` (dev). |
| 2.7 | **Set up design tokens** | `mobile_spec/FIGMA_PAGE_STRUCTURE_COMPONENTS.md` → "02 -- Brand + Tokens". Core tokens: Background/Surface/Elevated Surface, Primary/Secondary/Tertiary text, Accent green, Severity colors (Mild/Moderate/Severe/Flare), Status colors (Success/Warning/Error/Info). Also: type scale, spacing scale, radius system, shadows, icon rules, motion rules. Color values from `mobile_spec/STYLE_GUIDE.md` → section 2. |
| 2.8 | **Set up styling** | `2opmd_mobile_spellbook.json` → `stack.recommended.styling`: StyleSheet or NativeWind (Tailwind for RN). Apply color tokens and typography from design tokens (2.7). |
| 2.9 | **Build foundations layer** | `mobile_spec/FIGMA_PAGE_STRUCTURE_COMPONENTS.md` → "03 -- Foundations". App shell, safe areas, top/bottom navigation patterns, grid/spacing system, card/input spacing rules, divider rules, empty state rules, microcopy rules. |
| 2.10 | **Set up tab navigation structure** | `2opmd_mobile_spellbook.json` → `screens.main_tabs`: Today, Journal, Timeline, Ask. Optional: Settings. Bottom nav (3 or 4 tab version): black bg, outline icons white, active = accent. See `mobile_spec/FIGMA_PAGE_STRUCTURE_COMPONENTS.md` → "A. Navigation" and `mobile_spec/STYLE_GUIDE.md` → section 4 "Bottom Navigation". |
| 2.11 | **Build core components** | `mobile_spec/FIGMA_PAGE_STRUCTURE_COMPONENTS.md` → "04 -- Components" + Components Checklist. Priority components for scaffold: buttons (primary/secondary/tertiary/icon), inputs (text/search/multiline/email), selection controls (radio card/pill/tag chips/emotion bubble/severity hold), cards (intro/metric/pattern/next step/trust/premium), feedback states (empty/loading/error/success). |

### Phase 3: Onboarding Flow (O1-O17)

| # | Task | Routing (Where to Find Everything) |
|---|---|---|
| 3.1 | **O1 -- Splash** | `mobile_spec/FIGMA_PAGE_STRUCTURE_COMPONENTS.md` → Screen Checklist O1. Off-white background, centered Great Oak symbol, no text, subtle heartbeat/pulse motion. |
| 3.2 | **O2 -- Welcome** | FIGMA spec O2. Small oak mark, headline ("Chronic symptoms deserve clarity."), subhead ("For autoimmune, chronic illness, and anyone still searching for answers."), primary CTA, secondary login link, micro trust line. Design commandments § 2. |
| 3.3 | **O3 -- Promise** | FIGMA spec O3. 3 compact cards showing what happens when they use it. Continue CTA, how-it-works link. |
| 3.4 | **O4 -- Credibility** | FIGMA spec O4. Headline, 2 proof tiles, optional learn-more link. Establishes more than a tracker. |
| 3.5 | **O5 -- Name** | FIGMA spec O5. Text field + continue. |
| 3.6 | **O6 -- Age** | FIGMA spec O6. Age range cards / radio rows + continue. |
| 3.7 | **O7 -- Gender Identity** | FIGMA spec O7. Female / male / another identity / prefer not to say. Text input shown only if "another identity" selected. |
| 3.8 | **O8 -- Diagnosed vs Searching** | FIGMA spec O8 + `prototype_scope_nate.must_have_modules.onboarding[0]`. Two large cards, one CTA, minimal copy. Design commandments § 2. |
| 3.9 | **O9A -- Diagnosed Path** | FIGMA spec O9A. Searchable diagnosis field, quick chips, credibility through breadth. |
| 3.10 | **O9B -- Searching Path** | FIGMA spec O9B. Short text explanation field, helper text with example. |
| 3.11 | **O10 -- 30-Day Bad-Day Map** | FIGMA spec O10 + `prototype_scope_nate.must_have_modules.onboarding[1]`. Month grid, severity legend, "estimate is fine" helper copy, counters, continue CTA. Design commandments § 4: flagship interaction. Components: 30-day map container, calendar day states (empty/bad/mild/moderate/severe/flare), legend row, severity hold state selector. |
| 3.12 | **O11 -- Emotional Context** | FIGMA spec O11 + `prototype_scope_nate.must_have_modules.onboarding[2]`. Bubble selection field, choose up to 5, clinical framing copy. Design commandments § 5. Component: emotion bubble selector. |
| 3.13 | **O12 -- Top Symptoms** | FIGMA spec O12 + `prototype_scope_nate.must_have_modules.onboarding[3]`. Search, chips, selected state. |
| 3.14 | **O13 -- Journaling Value** | FIGMA spec O13 + `prototype_scope_nate.must_have_modules.onboarding[4]`. Headline, 3 bullet cards, continue CTA, optional example summary link. Design commandments § 6. |
| 3.15 | **O14 -- 3-Day Baseline Commitment** | FIGMA spec O14. Short mission card, "Start 3-day baseline" CTA. |
| 3.16 | **O15 -- Save Progress** | FIGMA spec O15 + `prototype_scope_nate.must_have_modules.onboarding[5]`. Apple / Google / Email options, privacy line. API: `POST /api/auth/register`. Design commandments § 3: value before setup. |
| 3.17 | **O16 -- Optional Records** | FIGMA spec O16 + `prototype_scope_nate.must_have_modules.onboarding[6]`. Upload PDF, upload image, skip for now. Mockable: real records parsing. Components: upload PDF card, upload image card. |
| 3.18 | **O17 -- Starting Snapshot** | FIGMA spec O17 + `prototype_scope_nate.must_have_modules.onboarding[7]`. What we know, what we'll watch, what improves accuracy, go to home CTA. Design commandments § 8. Can be mocked. |

### Phase 4: Home + Core Loop (H1-H5)

| # | Task | Routing (Where to Find Everything) |
|---|---|---|
| 4.1 | **H1 -- Home** | FIGMA spec H1. Tree + streak, today check-in card, patterns emerging card, next step card, collapsed timeline preview, advanced analysis CTA, prepare for visit CTA. Design commandments § 9: radically simple home. Components: oak tree states, streak counter badge, signal strengthening label, metric summary card, pattern insight card, next step card. |
| 4.2 | **H2 -- 2-Second Check-In** | FIGMA spec H2 + `prototype_scope_nate.must_have_modules.home[0]`. Physical slider (0-10), optional toggles, save CTA. Design commandments § 7: tiny daily loop (10s basic). Components: 0-10 physical slider, quick toggles row, save confirmation micro-toast. |
| 4.3 | **H3 -- Emotional Check-In** | FIGMA spec H3. Bubble field, quick save. Component: emotional bubble field. |
| 4.4 | **H4 -- Structured Journal** | FIGMA spec H4 + `prototype_scope_nate.must_have_modules.home[1]`. 4 modules (symptom shift, trigger selection, context note, environment/behavior), optional attachments, completion CTA. API: `POST /GET /DELETE /api/journal`. Design commandments § 6: 4-part structured journal. Components: symptom shift module, trigger selection module, context note module, environment/behavior module, optional add-photo/file attachment trigger. |
| 4.5 | **H5 -- Journal Confirmation** | FIGMA spec H5. Subtle success state, watered tree animation, one-line intelligent acknowledgement. Component: tree watering micro-animation. |

### Phase 5: Analysis + Visit Prep + Monetization (H6-H10, M1-M2)

| # | Task | Routing (Where to Find Everything) |
|---|---|---|
| 5.1 | **H6 -- Patterns Emerging** | FIGMA spec H6 + `prototype_scope_nate.must_have_modules.home[2]`. One-sentence insight, not-enough-data variant, confidence/clarity hints. API: `GET /api/timeline/eoh/flarereport/{patient_id}`. Design commandments § 8: "My data is becoming signal." Components: pattern insight card, pattern clarity meter, confidence meter. |
| 5.2 | **H7 -- Advanced Analysis** | FIGMA spec H7 + `prototype_scope_nate.must_have_modules.home[3]`. Consistency, pattern clarity, confidence, evidence summary, what changed, what improves accuracy, what to ask next. API: `GET /api/timeline/eoh/landscape/{patient_id}`, `GET /api/timeline/eoh/flareprediction/{patient_id}`. Can be mocked. Components: consistency meter, confidence meter, evidence summary block, what changed block, what improves accuracy block, questions to ask block. |
| 5.3 | **H8 -- Prepare for Visit** | FIGMA spec H8 + `prototype_scope_nate.must_have_modules.other[0]`. Summary card preview, timeline snapshot, top patterns, recent changes, questions to ask, export CTA. Design commandments § 12: "holy-shit feature." Can be mocked. Components: clinician summary card. |
| 5.4 | **H9 -- Timeline Detail** | FIGMA spec H9. Event rows, pattern markers, symptom spikes, context chips. Components: timeline preview row, timeline event card. |
| 5.5 | **H10 -- Records / Upload Center** | FIGMA spec H10. Uploaded docs list, processing states, parsed preview, connect provider entry point. Components: upload PDF card, upload image card, portal connect card, file processing state, parsed results preview, upload error state. |
| 5.6 | **M1 -- Day 3 First Pattern Moment** | FIGMA spec M1 + `prototype_scope_nate.must_have_modules.other[1]`. Headline: first pattern detected, one meaningful insight, see more CTA. Design commandments § 8. Components: first pattern modal. |
| 5.7 | **M2 -- Premium Offer** | FIGMA spec M2 + `prototype_scope_nate.must_have_modules.other[2]`. 7-day free trial positioning, deeper analysis benefits, clinician export benefits, longer horizon benefits, continue with basic mode. Design commandments § 13: no paywall before value. Components: trial offer card, premium features comparison, continue with basic mode button. |
| 5.8 | **States + Edge Cases** | FIGMA spec page 09. Loading, empty, partial, offline, upload failure, no pattern yet, not enough data, disconnected record source. Components: empty state, not enough data yet state, partial data state, loading skeleton, error state, success state. |

### Phase 6: Auth, API Wiring

| # | Task | Routing (Where to Find Everything) |
|---|---|---|
| 6.1 | **Login screen** | `2opmd_mobile_spellbook.json` → `screens.auth.Login`: "Email + password. POST /api/auth/token. Store JWT." Mobile login: `POST /api/auth/token/mobile` (7-day expiry). JWT stored in expo-secure-store. |
| 6.2 | **Registration (optional for prototype)** | `screens.auth.Register`: "Optional for prototype. Can gate behind feature flag." API: `POST /api/auth/register`. |
| 6.3 | **Wire API base** | `2opmd_mobile_spellbook.json` → `architecture.api_base`: `EXPO_PUBLIC_API_BASE` env var. Dev: `http://localhost:8000`. Prod: `2ndopinionmd.ai`. Use ngrok or tunnel for local dev with physical device. |
| 6.4 | **Wire auth headers** | `2opmd_mobile_spellbook.json` → `devin_instructions.constraints`: "JWT in Authorization header: Bearer <token>". All authenticated endpoints require this header. |
| 6.5 | **Wire journal API** | `api_endpoints.journal`: create (`POST`), list (`GET`), get (`GET /{entry_id}`), delete (`DELETE /{entry_id}`), ai_query (`POST /query-ai`), timeline (`GET /timeline/{report_id}`). |
| 6.6 | **Wire timeline API** | `api_endpoints.timeline`: get (`GET /{patient_id}`), add_events (`POST /{patient_id}/events`), flare_report, flare_prediction. |
| 6.7 | **CORS update** | `2opmd_mobile_spellbook.json` → `architecture.cors`: "Backend CORS must allow mobile origin (Expo dev: exp://)". Update backend `cors_origins` if needed. |

### Phase 7: Ask Tab + SSE

| # | Task | Routing (Where to Find Everything) |
|---|---|---|
| 7.1 | **Build AskInput component** | `2opmd_mobile_spellbook.json` → `components.AskInput`: "Text input for clinical question. Submit triggers ask_stream. When user has journal entries: pass include_journal_context=1." |
| 7.2 | **Build StreamingAnswer component** | `components.StreamingAnswer`: "SSE consumer. Show status + streaming text. Same contract as web." SSE events: phase_start, retrieval_summary, reasoning_progress, llm_chunk, completion. |
| 7.3 | **Wire SSE endpoint** | `api_endpoints.rag_streaming.ask_stream`: `GET /api/rag/ask_stream`. Params: `q`, `limit`, `with_llm=1`, `llm_mode=chunk`. Optional: `include_journal_context=1`. |
| 7.4 | **Handle SSE in React Native** | `stack.sse_note`: no native EventSource in RN. Use `react-native-sse` or fetch + ReadableStream polyfill. Handle reconnection, show partial results. |
| 7.5 | **Build ErrorDisplay** | `components.ErrorDisplay`: "Honest failure. Cause + recovery. No softening." Network errors, API errors, SSE connection errors. |

### Phase 8: Test Against Backend

| # | Task | Routing (Where to Find Everything) |
|---|---|---|
| 8.1 | **Verify backend health** | `devin_instructions.testing.backend`: `curl http://localhost:8000/api/health`. |
| 8.2 | **Test auth flow** | `devin_instructions.testing.auth`: `POST /api/auth/token` with valid credentials. Verify JWT storage and retrieval. |
| 8.3 | **Test journal CRUD** | `devin_instructions.testing.journal`: `POST /api/journal` with auth header. Verify create, list, get, delete. |
| 8.4 | **Test ASK streaming** | `devin_instructions.testing.ask`: `GET /api/rag/ask_stream?q=test&with_llm=1`. Verify SSE events render correctly. Test with `include_journal_context=1` when entries exist. |
| 8.5 | **Test on device/emulator** | Run on iOS Simulator and/or Android Emulator via Expo. Verify onboarding flow, daily check-in, journal, ask tab. |

---

## ROUTING INDEX (Quick Reference)

| What You Need | Where It Lives |
|---|---|
| Full mobile build spec | `2opmd_mobile_spellbook.json` |
| Must-have modules + mockable items | `2opmd_mobile_spellbook.json` → `prototype_scope_nate` |
| All API endpoints (mobile) | `2opmd_mobile_spellbook.json` → `api_endpoints` |
| All API endpoints (full) | `2opmd_spellbook.json` → `api_endpoints` |
| Screen definitions | `2opmd_mobile_spellbook.json` → `screens` |
| User flows | `2opmd_mobile_spellbook.json` → `flows` |
| Component specs | `2opmd_mobile_spellbook.json` → `components` |
| Stack + dependencies | `2opmd_mobile_spellbook.json` → `stack` |
| SSE streaming contract | `ASK_STREAMING_CONTRACT.md` (web contract, same events for mobile) |
| Figma page structure + components checklist | `mobile_spec/FIGMA_PAGE_STRUCTURE_COMPONENTS.md` |
| Screen checklists (O1-O17, H1-H10, M1-M2) | `mobile_spec/FIGMA_PAGE_STRUCTURE_COMPONENTS.md` → Screen Checklists |
| Components checklist (13 categories, 80+ items) | `mobile_spec/FIGMA_PAGE_STRUCTURE_COMPONENTS.md` → Components Checklist |
| Motion rules | `mobile_spec/FIGMA_PAGE_STRUCTURE_COMPONENTS.md` → Motion Checklist |
| Copy system rules | `mobile_spec/FIGMA_PAGE_STRUCTURE_COMPONENTS.md` → Copy System Rules |
| Design tokens (brand + visual truth) | `mobile_spec/FIGMA_PAGE_STRUCTURE_COMPONENTS.md` → "02 -- Brand + Tokens" |
| Build order recommendation | `mobile_spec/FIGMA_PAGE_STRUCTURE_COMPONENTS.md` → Build Order Recommendation |
| Non-negotiables (10 items) | `mobile_spec/FIGMA_PAGE_STRUCTURE_COMPONENTS.md` → Non-Negotiables |
| Style reference (colors, typography, components) | `mobile_spec/STYLE_GUIDE.md` |
| Style reference images | `mobile_spec/*.jpg` (How We Feel — reference only, do NOT replicate screens) |
| Design north star (not yet canonical) | `mobile_spec/2opmd_design_commandments.md` |
| UX invariants (hard rules) | `2opmd_spellbook.json` → `ux_invariants.hard_rules[]` |
| Mobile UX additions | `2opmd_mobile_spellbook.json` → `ux_invariants.mobile_additions` |
| Devin build priority order | `2opmd_mobile_spellbook.json` → `devin_instructions.priority_order` |
| Devin constraints | `2opmd_mobile_spellbook.json` → `devin_instructions.constraints` |
| Testing commands | `2opmd_mobile_spellbook.json` → `devin_instructions.testing` |
| Environment variables | `2opmd_mobile_spellbook.json` → `environment` |
| Backend entry point | `server/api/app_postgres.py` |
| Auth routes (backend) | `server/api/auth_routes_postgres.py` |
| Journal routes (backend) | `server/api/journal.py` |
| RAG streaming routes (backend) | `server/api/rag_stream_routes.py`, `server/api/rag_stream_custom_endpoints.py` |
| Timeline routes (backend) | `server/api/timeline_routes.py` |
| Competitive synthesis (what to steal/avoid) | `mobile_spec/FIGMA_PAGE_STRUCTURE_COMPONENTS.md` → "What We Are Borrowing" |
| Spellbook spec report (gaps) | `reports/REPORT_MOBILE_SPELLBOOK_SPEC_20260306.md` (not yet in repo) |
| Figma (compiled screenshots) | [2opmd.app.figma](https://www.figma.com/design/ek23oisUl8U91A5WW3oo7m/2opmd.app.figma?node-id=0-1&p=f) |

---

## CONSTRAINTS (Non-Negotiable, from Mobile SpellBook + Figma Spec)

### From Mobile SpellBook
1. Do NOT add analytics or tracking
2. Do NOT fake loading states — no optimistic UI, no fake progress bars
3. Do NOT use axios — fetch only
4. JWT in Authorization header: `Bearer <token>`
5. SSE: handle reconnection, show partial results
6. Modes do not share state
7. Modes do not auto-transition
8. No session persistence across queries
9. No "remembering your preferences"
10. Failures surfaced honestly — stop, state cause, state recovery paths
11. Export is one-way transmission with no feedback loop
12. Only contract-specified events affect UI display
13. Style guide images are **reference only** — from How We Feel app. Apply visual language to 2OPMD flows; do NOT build those screens
14. Design commandments are **not yet canonical** — use as design intent background; spellbook + prototype_scope_nate are build authority
15. Offline: show cached data if any, else honest "no connection"
16. Pull-to-refresh where applicable
17. Keyboard handling: dismiss on scroll, don't obscure inputs
18. Backend/inference can be mocked — prototype should feel real

### From Figma Page Structure + Components Spec (Non-Negotiables)
19. The app must feel premium
20. The app must feel medically serious
21. The daily loop must be tiny
22. Journaling must feel useful, not decorative
23. Emotional context must feel legitimate, not fluffy
24. Home must stay minimal
25. The tree must represent consistency only
26. "Prepare for visit" must remain central
27. Trust language must be plainspoken
28. Value must come before monetization

### Motion Rules
- Include: splash pulse, button press depth, card entrance fade/rise, tree watering micro-animation, bubble selection animation, severity hold feedback on calendar, save confirmation toast fade, smooth modal sheet transitions
- Avoid: flashy gradient motion, gamified confetti, excessive bounce, cute personality animations

### Copy System
- Use: calm, sharp, brief, clinically serious, emotionally safe
- Avoid: hype, startup jargon, wellness fluff, over-explaining, therapy-app softness

---

## READINESS STATUS

| Item | Status |
|---|---|
| Mobile SpellBook ingested | YES |
| Handoff ingested | YES |
| Prototype scope (Nate) ingested | YES |
| Style guide read (reference only) | YES |
| Design commandments read (not yet canonical) | YES |
| Parent SpellBook ingested | YES |
| Figma link captured | YES |
| Figma page structure + components ingested | YES |
| Expanded onboarding screens mapped (O1-O17) | YES |
| Core product screens mapped (H1-H10) | YES |
| Monetization screens mapped (M1-M2) | YES |
| Components checklist cataloged (80+ items) | YES |
| Motion rules cataloged | YES |
| Copy system rules cataloged | YES |
| Non-negotiables (10 from Figma spec) cataloged | YES |
| Build order recommendation ingested | YES |
| Competitive synthesis ingested | YES |
| Spellbook spec report ingested | NO — not yet in repo |
| All API endpoints mapped | YES |
| All component specs located | YES |
| All screen definitions mapped | YES |
| All user flows understood | YES |
| Stack + dependencies identified | YES |
| SSE streaming contract understood | YES |
| Constraints cataloged | YES |
| Build priority order understood | YES |
| Mockable items identified | YES |

**Ready to execute. Awaiting tasking.**
