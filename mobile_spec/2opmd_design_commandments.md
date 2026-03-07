# 2OPMD Design Commandments

Version: v1.0  
Audience: Nate, Andras, Dylan, Devin  
Purpose: Team-ready design north star for the 2OPMD mobile prototype and early production app

---

## TLDR

**2OPMD should be:**
- Guava’s seriousness
- Visible’s daily usefulness
- Bearable’s multi-factor pattern logic
- Daylio’s frictionless habit loop
- How We Feel’s emotional legitimacy
- Apple Health’s visual restraint

**2OPMD should not be:**
- a generic symptom tracker
- a mood app
- a wellness app
- a journaling toy
- a dashboard swamp
- a black-box AI wrapper

**Core product truth:**  
2OPMD turns daily chronic illness reality into a timeline your doctor can actually use.

**Core UX truth:**  
The user should feel seen immediately, guided quickly, less overwhelmed, smarter over time, and better prepared for appointments.

**Core design truth:**  
One job per screen. One primary action per screen. Fewer words. More clarity. More signal. More restraint.

**Core retention truth:**  
Users keep using 2OPMD when they feel their bad days are becoming less random, their journal is creating useful signal, and their next doctor visit will be better.

---

## 1. 2OPMD is a clinical timeline engine

This is the first commandment because it kills bad design decisions early.

2OPMD is:
- a premium mobile app for chronic illness, autoimmune disease, and medically confused users
- built to track patterns across time
- built to support clinician conversations
- powered by a real longitudinal reasoning layer

2OPMD is not:
- an AI health buddy
- a symptom journal
- a mood tracker
- a general wellness dashboard
- a black-box chatbot

### Internal shorthand
**Not a journal. Not a chatbot. A timeline engine.**

---

## 2. Say who it’s for immediately

The app must clearly call out:
- autoimmune
- chronic illness
- people still searching for answers
- diagnosed users who want fewer flare surprises and more control

The app should not open with vague “take control of your health” language.

### Best opening line
**Chronic symptoms deserve clarity.**

### Best subhead
**For autoimmune, chronic illness, and anyone still searching for answers.**

### User reaction we want
- This is for people like me.
- This is not generic.
- This understands the kind of mess I’m in.

---

## 3. Give value before setup

Do not make users create accounts, connect systems, and configure categories before they feel the product helping.

### Correct order
1. Diagnosed vs searching
2. 30-day bad-day map
3. Emotional context
4. Top symptoms
5. Journaling value
6. Early snapshot
7. Save account
8. Optional records upload

### Why
Signal first. Plumbing second.

The user should feel:
- this is already helping
before
- please do setup work

---

## 4. The 30-day bad-day map is a flagship interaction

This is one of the strongest product ideas in the app.

### Why it works
It immediately feels:
- serious
- analytical
- relevant
- pattern-driven
- not like a wellness toy

### Interaction model
- tap = bad day
- hold = set severity
  - mild
  - moderate
  - severe
  - flare

### Required tone
The UI must communicate:
- Estimate is fine.
- It doesn’t need to be perfect.
- We’re looking for signal, not perfection.

### Design rule
Make it feel premium and tactile, not gamified.

---

## 5. Emotional context belongs in the product, but not at the center

Emotions, stress, sleep disruption, and overwhelm matter. They can amplify symptoms, affect behavior, and shape how people experience a flare.

That makes the emotional layer valid.

But 2OPMD is not a mood app.

### Correct role of emotional context
- support the health story
- add signal
- add context
- help separate signal from noise

### Correct placement
Put emotional context **after** the 30-day bad-day map.

That sequencing says:
- first, this is about your health
- second, emotional context helps interpret it

### Best framing
Use language like:
- Stress and emotion can amplify symptoms.
- This helps us separate signal from noise.
- Select up to 5 that reflect how you’ve felt overall lately.

Avoid any language that feels soft, cutesy, or therapy-first.

---

## 6. Journaling is one of the engines

The journal is not optional garnish.

It should feel like:
- leverage
- context
- intelligence
- one of the main reasons the app gets smarter over time

### Product truth
Symptoms alone rarely tell the whole story.

### The journal should help capture
- symptom shifts
- stress
- sleep
- triggers
- meds
- behavior changes
- unusual context
- language patterns
- possible psych amplification

### Design rule
Do not default to a giant blank text box.

### Best format
Use a **4-part structured journal**:
1. symptom shift
2. likely trigger or context
3. short reflection
4. environmental or behavioral factor

This keeps the journal:
- clinically useful
- fast enough
- emotionally safe
- interpretable later

---

## 7. The daily loop must be tiny

If the daily loop feels like homework, the app loses.

### Correct daily loop
1. physical check-in
2. optional emotional context
3. optional structured journal
4. done

### Target duration
- 10 seconds for basic daily use
- 30 to 60 seconds for fuller context

### Desired feeling
- easy enough to do when tired
- useful enough to matter
- small enough to repeat

This is where 2OPMD should borrow from Daylio and Visible.

---

## 8. Show the user that signal is building

A lot of apps fail here. Users log data into a void.

2OPMD must make the user feel:
- the app is learning something
- signal is strengthening
- patterns are emerging
- their next doctor visit is getting better

### Core feedback surfaces
- Patterns emerging
- What we’re watching
- What improves accuracy
- First pattern detected
- Prepare for visit
- Advanced Analysis

### Core user feeling
My data is becoming signal.

Not:
I’m feeding a machine for free.

---

## 9. Keep the home screen radically simple

Home is the cockpit, not the maintenance room.

### Home should include
- Tree / consistency
- Today’s check-in
- Patterns emerging
- Next step
- Advanced Analysis
- Prepare for visit
- optional collapsed timeline preview

### Home should not include
- every symptom category
- every chart
- every journal card
- every advanced metric
- every filter
- a wall of controls

### Desired feeling
- calm
- premium
- navigable
- obvious

---

## 10. The Tree of Life rewards consistency, not health status

### The tree means
- consistency
- continuity
- signal strength
- resilience
- time invested

### The tree does not mean
- your symptoms are better
- you are healthier today
- you are morally succeeding
- you are in remission

A user can have a terrible week and still build the tree.

That is exactly how it should work.

### Product rule
The tree should grow subtly.
No cartoon chaos. No mascot trap. No pet vibes.

Elegant. Symbolic. Adult.

---

## 11. Trust must be plainspoken

The best trust language is simple, calm, and specific.

### Best trust phrases
- Private by design
- You control what you share
- Built to support your clinician conversation
- Not a black box
- See what drove the insight

### Worst trust style
- startup AI mush
- giant compliance word salads
- legalese in the main UX

### Best placement
- welcome
- save account
- upload records
- advanced analysis
- prepare-for-visit flow

---

## 12. Prepare for visit is a holy-shit feature

This is one of the strongest product truths in 2OPMD.

Users do not need more health data.
They need a clearer story and a better appointment.

### The output should include
- timeline snapshot
- recent changes
- top patterns
- possible triggers or correlations
- questions to ask
- what to investigate next

### Product rule
This feature should not feel buried.
It should be one of the main things the app can do.

---

## 13. Premium should unlock depth, not oxygen

The app should not ransom the user before the habit forms.

### Correct monetization posture
- no hard paywall in onboarding
- no payment before the user feels real value
- premium comes after a first pattern / first insight / first doctor-useful moment

### Premium should unlock
- deeper trigger mapping
- longer-horizon pattern views
- richer evidence summaries
- clinician export / PDF
- deeper advanced analysis

### Not ideal
- gating basic habit formation
- paywalling the emotional core of the app
- charging before the app demonstrates signal

---

## 14. Be more premium than the competition

### Guava
Strong on seriousness and provider collaboration.
2OPMD opportunity: more premium and more emotionally intelligent.

### Visible
Strong on daily usefulness and chronic seriousness.
2OPMD opportunity: broader scope, better interpretive layer.

### Bearable
Strong on correlation logic and breadth.
2OPMD opportunity: less cognitive load, more guidance.

### Daylio
Strong on ease and repetition.
2OPMD opportunity: same ease, higher medical seriousness.

### How We Feel
Strong on emotional legitimacy.
2OPMD opportunity: connect emotion directly to chronic-health context.

### Apple Health
Best-in-class visual trust benchmark.
2OPMD opportunity: more specific, more narrative, more doctor-ready.

---

## 15. Narrate better than the competition

A lot of apps can:
- log
- chart
- color-code
- export

Far fewer can tell the user:
- Here’s what seems to be changing.
- Here’s what may be driving it.
- Here’s what we’re confident in.
- Here’s what we’re unsure about.
- Here’s what to ask next.
- Here’s what would improve accuracy.

That narrative layer is one of 2OPMD’s biggest opportunities.

---

# What to steal from each app

## From Guava
Steal:
- seriousness
- whole-picture framing
- provider collaboration energy
- validation of the undiagnosed / complex chronic ICP

Do not steal:
- too much operational setup too early

## From Visible
Steal:
- daily reason to open
- practical chronic-care usefulness
- reports that matter

Do not steal:
- narrow pacing-only identity

## From Bearable
Steal:
- multi-factor trigger logic
- breadth of possible inputs
- “what makes me better or worse?” framing

Do not steal:
- setup sprawl
- interface overload

## From Daylio
Steal:
- micro-check-ins
- low typing burden
- habit ease
- visual summaries

Do not steal:
- mood-app softness
- self-help vibe

## From How We Feel
Steal:
- emotional nuance
- science-backed tone
- elegant emotional interactions
- plain-language trust

Do not steal:
- a psychology-first product identity

## From Apple Health
Steal:
- layout restraint
- trust tone
- summary-first hierarchy
- calm charts and trends
- state-of-mind legitimacy

Do not steal:
- generic broadness
- passive product feel

---

# What goes into v1

## Must-have
- splash
- welcome
- promise / why different
- diagnosed vs searching
- 30-day bad-day map
- emotional context
- top symptoms
- journaling value
- save account
- optional records upload
- starting snapshot
- home
- daily check-in
- structured journal
- patterns emerging
- advanced analysis
- prepare for visit
- Day 3 first-pattern moment
- premium upsell

## Nice-to-have
- widget
- reminders
- richer timeline detail
- more visual growth states for tree
- lightweight mock data variants

## Not yet
- overbuilt gamification
- provider workflow integration
- deep EHR connectivity as a prerequisite
- giant analytics dashboard
- bloated prototype complexity

---

# Final design commandments, condensed

1. Start with the right audience.
2. Give value before setup.
3. Make the daily loop tiny.
4. Treat journaling like signal.
5. Use emotional context seriously.
6. Show signal building.
7. Keep home minimal.
8. Make trust plainspoken.
9. Build toward the doctor visit.
10. Reward consistency, not health status.
11. Monetize after value.
12. Stay premium, adult, and restrained.

---

# Final one-line design brief

**Build 2OPMD as a premium chronic-illness timeline engine that feels as easy as Daylio, as useful daily as Visible, as comprehensive as Guava and Bearable, as emotionally legitimate as How We Feel, and as visually trustworthy as Apple Health.**

---

# Team note

This document is the design north star.
It is not meant to freeze creativity.
It is meant to stop drift.

If a design decision makes 2OPMD feel more like:
- a mood app
- a journaling toy
- a dashboard swamp
- a black-box chatbot

…it is probably wrong.

If a design decision makes 2OPMD feel more like:
- a premium chronic-care intelligence layer
- a clearer story over time
- a better doctor visit waiting to happen

…it is probably right.
