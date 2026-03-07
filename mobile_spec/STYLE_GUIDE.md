# 2OPMD Mobile Prototype — Style Guide

**Derived from:** `mobile_spec/` reference images (How We Feel app patterns)  
**For:** Devin (React Native build)  
**Date:** 2026-03-06

---

## Important: Style Reference Only

**These images are style references, not a spec to implement.** They are from a different app (How We Feel) with different functionality. Nate chose them because he likes the visual style. Use them for visual inspiration only — colors, typography, component shapes, layout feel. Do NOT build the 2OPMD app to match those screens functionally. Build the 2OPMD flows (onboarding, Today, Journal, Timeline, Ask) from the spellbook and prototype_scope_nate; apply this visual language to those flows.

**Provenance:** These images are publicly available (unlike the leaked Guava app Figma, which was considered earlier and is not in use). Nate is willing to break rules that Dylan is not. Dylan is treating IP integrity seriously and believes we are in the clear to use these for style reference. **2OPMD Figma:** https://www.figma.com/design/ek23oisUl8U91A5WW3oo7m/2opmd.app.figma?node-id=0-1&p=f — compiled screenshots; Devin can reference.

---

## 1. Theme

- **Primary:** Dark mode first. Background `#000000`.
- **Tone:** Clinical, clean, modern. Friendly but not playful. High contrast, no fluff.
- **Philosophy:** Same as 2OPMD web — honest, minimal, data-focused.

---

## 2. Color Palette

| Token | Hex | Use |
|-------|-----|-----|
| `--bg-primary` | `#000000` | Main background |
| `--bg-container` | `#1A1A1A` | Cards, modals, elevated surfaces |
| `--text-primary` | `#FFFFFF` | Headlines, body, labels |
| `--text-secondary` | `#AAAAAA` | Secondary actions, "Skip setup" |
| `--text-muted` | `#A0A0A0` | Body copy, captions |
| `--accent-primary` | `#4A90D9` | Primary actions, links (2OPMD blue) |
| `--accent-success` | `#4CAF50` | Battery, success, active nav |
| `--accent-amber` | `#F5A623` | Check-in progress, streak |
| `--button-bg` | `#FFFFFF` | Primary button background |
| `--button-text` | `#000000` | Primary button text |
| `--separator` | `#333333` | Dividers, borders |
| `--emotion-warm` | `#E76F51` / `#FF7043` | Negative/intense emotions |
| `--emotion-cool` | `#7093E1` / `#56B9B7` | Calm, introspective |
| `--emotion-positive` | `#81C784` / `#4CAF50` | Positive, energized |

**Emotion bubbles:** Use gradient families — red/pink (negative), olive/green (positive), teal/blue (calm). Vary by category, not random.

---

## 3. Typography

| Role | Font | Weight | Size | Color |
|------|------|--------|------|-------|
| **Headline** | Serif (Georgia, Lora, Playfair Display) | Bold | 28–34pt | `#FFFFFF` |
| **Section title** | Serif | Bold | 22–26pt | `#FFFFFF` |
| **Body** | Sans-serif (SF Pro, Inter, Roboto) | Regular | 16–18pt | `#FFFFFF` |
| **Label** | Sans-serif | Medium | 14–16pt | `#FFFFFF` |
| **Button** | Sans-serif | Bold/Medium | 18pt | `#000000` on white |
| **Secondary action** | Sans-serif | Regular | 14pt | `#AAAAAA` |
| **Caption / small** | Sans-serif | Regular | 12–13pt | `#A0A0A0` |
| **Link** | Sans-serif | Regular | 16pt | `#007AFF` (or accent) |

**Rule:** Serif for headlines and value props. Sans-serif for UI, body, buttons.

---

## 4. Components

### Buttons

- **Primary:** Full-width, pill-shaped (border-radius ≈ half height). White bg, black text. Min height 52px.
- **Secondary:** Outlined — thin white border, transparent bg, white text.
- **Text link:** Underlined, accent or white.

### Emotion Bubbles (for 2-second check-in, emotion context)

- **Shape:** Circles (primary). Irregular polygon for selected/focal (e.g. octagon).
- **Layout:** Organic cluster, not rigid grid. Varying sizes — larger = selected or emphasized.
- **Colors:** Category-coded (warm/cool/positive). Text dark gray or black on colored bg for contrast.
- **Interaction:** Tap to select. Selection indicated by size increase or shape change.

### Progress Indicator

- **Style:** Thin white horizontal line. Filled segment = progress.
- **Step label:** "X/Y" in white, sans-serif, small.

### Cards / Containers

- **Background:** `#1A1A1A` or `#2C2C2C`.
- **Border radius:** 12–16px for cards, 8px for grid items.
- **Padding:** 16–24px.

### Bottom Navigation

- **Background:** Black.
- **Icons:** Outline style, white. Active = accent (e.g. green or amber).
- **Labels:** Below icons, sans-serif, small.

### Tooltip / Speech Bubble

- **Background:** White.
- **Text:** Black.
- **Shape:** Rounded rect with pointed tail.

---

## 5. Layout

- **Padding (horizontal):** 20–24px from screen edges.
- **Vertical spacing:** 24–32px between sections, 16–20px between list items.
- **Alignment:** Headlines and body left-aligned. Buttons centered. Content stacked vertically.
- **Negative space:** Generous. Avoid clutter.

---

## 6. Iconography

- **Style:** Minimalist line art. Thin stroke. No fill except for active states.
- **Color:** White default. Accent for active/highlight.
- **Size:** 24px standard, 20px small.
- **Examples:** Back arrow, X (dismiss), + (add), magnifying glass (search).

---

## 7. Illustrations (Optional for 2OPMD)

Reference images use abstract blob characters with gradient fills and white line-art limbs. 2OPMD may prefer: no characters, or simplified clinical icons. If using illustrations: soft gradients, rounded shapes, minimal line art.

---

## 8. Image Reference Manifest

| Name | Screen / Module |
|------|-----------------|
| `logo_gradient_heart_checkmark.jpg` | App icon / splash |
| `onboarding_welcome_how_we_feel.jpg` | Onboarding welcome |
| `onboarding_welcome_hi.jpg` | Setup intro |
| `onboarding_why_are_you_here.jpg` | Diagnosed vs searching / goal selection |
| `onboarding_benefits_help_you.jpg` | Journaling value prop |
| `onboarding_strategies_moment.jpg` | Strategies / in-the-moment |
| `onboarding_free_donations.jpg` | Free / donations value |
| `onboarding_terms_privacy.jpg` | Terms & Privacy |
| `onboarding_ai_features_opt_in.jpg` | AI opt-in (premium / advanced) |
| `onboarding_share_emotions_friends.jpg` | Social sharing intro |
| `onboarding_widget_checkin_promo.jpg` | 2-second check-in widget promo |
| `onboarding_add_widget.jpg` | Add widget |
| `onboarding_search_how_we_feel.jpg` | Search / discovery |
| `emotion_context_word_cloud.jpg` | Emotion context — word cloud |
| `emotion_context_bubbles_*.jpg` | Emotion context — bubble picker (variants) |
| `emotion_bubble_selection_*.jpg` | Emotion selection by category |
| `emotion_patterns_insights.jpg` | Patterns emerging |
| `home_daily_checkin_circle.jpg` | 2-second check-in — main CTA |
| `home_daily_checkin_tools_tooltip.jpg` | Check-in + tools tooltip |
| `home_grid_selector_empty.jpg` | Customizable home grid |
| `home_bottom_nav.jpg` | Tab bar |
| `home_analyze_chart.jpg` | Advanced analysis |
| `home_journal_entry.jpg` | Structured journal |
| `home_patterns_analyze.jpg` | Patterns card |
| `home_emotion_streak.jpg` | Streak / retention |

---

## 9. Devin Quick Reference

1. **Background:** Always `#000000` unless elevated surface.
2. **Headlines:** Serif, bold, white.
3. **Buttons:** Pill-shaped, white bg, black text.
4. **Emotion picker:** Circular bubbles, color-coded, organic cluster.
5. **Progress:** Thin white line + "X/Y".
6. **Nav:** Bottom bar, outline icons, accent for active.
7. **No:** Optimistic UI, fake progress, decorative clutter.
