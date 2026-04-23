# HANDOFF: Devin Mobile — React Native Prototype Build

**Date:** 2026-03-06  
**From:** Dylan (via Cursor/Auto)  
**To:** Devin (Cognition)  
**Purpose:** Handoff for 2OPMD React Native prototype. Create REPORT_READINESS_MOBILE.md before build.

---

## First Task: Create REPORT_READINESS_MOBILE.md

Before starting the build, create `reports/REPORT_READINESS_MOBILE.md` in the 2ndOpinionMD-MVP repo, structured like `reports/REPORT_READINESS.md`.

### Required Sections

1. **SOURCES INGESTED** — Table of documents with location and summary. Include:
   - `2opmd_mobile_spellbook.json` (build spec, API, flows, constraints)
   - `HANDOFF_DEVIN_MOBILE.md` (this document)
   - `prototype_scope_nate` (must-have modules, mockable backend)
   - `mobile_spec/STYLE_GUIDE.md` (style reference only; images from different app)
   - `mobile_spec/2opmd_design_commandments.md` (Nate's design north star; not yet canonical)
   - `reports/REPORT_MOBILE_SPELLBOOK_SPEC_20260306.md` (gaps, recommendations)
   - `2opmd_spellbook.json` (parent; shared backend, API contracts)
- **Figma:** https://www.figma.com/design/ek23oisUl8U91A5WW3oo7m/2opmd.app.figma?node-id=0-1&p=f — compiled screenshots; Devin can reference

2. **TASK LIST (Execution Order)** — Phases with numbered tasks and Routing columns. Follow the spellbook's priority_order and prototype_scope_nate. Phases should map to:
   - Phase 1: Read / ingest (spellbook, scope, style guide, report)
   - Phase 2: Scaffold React Native (Expo)
   - Phase 3: Onboarding flow
   - Phase 4: Home (Today, check-in, journal, patterns, advanced analysis)
   - Phase 5: Other (prepare for visit, Day 3 first-pattern, premium upsell)
   - Phase 6: Auth, API wiring
   - Phase 7: Ask tab + SSE
   - Phase 8: Test against backend

   Each task row: `| # | Task | Routing (Where to Find Everything) |`

3. **ROUTING INDEX** — Quick reference table: "What You Need" → "Where It Lives"

4. **CONSTRAINTS** — Non-negotiable items from spellbook (no analytics, no axios, no fake loading, etc.)

5. **READINESS STATUS** — Checkboxes for sources ingested, constraints understood, etc. End with "Ready to execute. Awaiting tasking." or equivalent.

### Reference Format

Use `reports/REPORT_READINESS.md` as the structural template. Adapt content for mobile: React Native, Expo, mobile_spec, prototype_scope_nate, style guide (reference only), design commandments (Nate's north star, not canonical).

---

## Key Caveats

- **Style guide:** Images in `mobile_spec/` are from How We Feel. Style reference only. Do NOT build those screens. Apply visual language to 2OPMD flows.
- **Design commandments:** Nate-created. Dylan reviewing. Not yet canonical. Use as design intent background; spellbook and prototype_scope_nate are build authority.
- **Build spec:** Spellbook + prototype_scope_nate. Whole story simply. Backend/inference can be mocked; prototype should feel real.

---

## After REPORT_READINESS_MOBILE.md

Once the readiness report is written, treat it as the execution checklist. Build in phase order. File receipts for milestones. Update the report with completion status as you go.
