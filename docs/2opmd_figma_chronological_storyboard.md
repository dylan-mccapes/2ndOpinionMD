# 2OPMD Figma Chronological Storyboard

## Positioning decision baked into this spec
- Keep the refined Oak Tree as the core symbol.
- Do not use a cartoon mascot.
- Do not use Eve, Adam, Glow, or any named character in v1.
- A subtle garden metaphor can exist later in the product as a visual world, but the onboarding should center on clinical clarity, not character-driven guidance.
- The emotional tone is early-Apple clarity applied to healthcare: simple, restrained, premium, empathetic, confident.

## Global visual system
### Backgrounds
- Primary background: soft off-white `#F7F8FA`
- Elevated cards: pure white `#FFFFFF`
- Subtle surface: `#F1F3F5`
- Border: `#E6E9EE`

### Typography
- Display / hero: strong modern sans serif, semibold to bold, charcoal `#121417`
- Secondary body: `#5B6572`
- Tiny helper text: `#8A94A3`
- Generous line height, generous vertical spacing, no cramped copy blocks

### Accent colors
- Primary accent / Oak green: `#1E3A34`
- Supporting sage: `#6D8B7F`
- Difficult day: `#9B534A`
- Flare day ring: `#7B342E`

### Visual constraints
- No gradients
- No cartoon illustration style
- No wellness app beige softness
- No playful mascot face
- No generic SaaS dashboard clutter
- No bright neon colors
- No glassmorphism

### Oak symbol rules
- Refined, minimal Oak Tree icon or emblem
- Slightly geometric and timeless
- No face, no eyes, no character personality
- Represents consistency only
- May appear in a soft line treatment, embossed mark, or subtle header motif

### Navigation rules
- Back button top-left where applicable
- Close / skip top-right only when skipping is allowed
- One primary CTA at bottom
- CTA anchored above safe area

### Motion rules
- Subtle only
- Watering the Oak after check-in or journal save
- No fake progress bars
- No playful bounce

---

## Image 1 - Splash
### Purpose
Create an immediate premium first impression and signal that this is not a generic symptom tracker.

### Design elements
- Full-screen off-white or very pale stone background
- Refined Oak Tree mark centered vertically, about 20% above center
- No extra text
- Optional extremely subtle embossed ring or halo behind the oak, low contrast only
- No button

### Text
- None

### Interaction
- Auto-advance after 1.2 to 1.8 seconds

### Notes for Figma
- Make the oak feel like a luxury medical brand mark, not a tree illustration.
- This should feel like opening a premium device, not launching an app.

---

## Image 2 - Welcome
### Purpose
Explain the product in one clean sentence and start the journey.

### Design elements
- Off-white background
- Oak mark top-center with generous breathing room
- Large centered headline
- Short centered subheadline
- Primary CTA button anchored near bottom
- Secondary text link below CTA
- Small trust line above safe area

### Text
- Headline: `Understand your health across time.`
- Subheadline: `2OPMD helps you track patterns between appointments so you and your doctor can make clearer decisions.`
- Primary CTA: `Get started`
- Secondary link: `I already have an account`
- Trust line: `Private by design. Built to work with your clinician.`

### Interaction
- Get started -> Image 3
- I already have an account -> Sign-in flow

### Notes for Figma
- This screen should be very light, very breathable, and very confident.
- Avoid over-explaining.

---

## Image 3 - Why 2OPMD is different
### Purpose
Establish category differentiation fast.

### Design elements
- Back button top-left
- Small oak mark top-center
- Large left-aligned headline
- Short body paragraph
- Three stacked credibility cards
- Primary CTA at bottom
- Small text link below CTA

### Text
- Headline: `More signal. Less guesswork.`
- Body: `Our proprietary longitudinal model looks across symptoms, stress, sleep, meds, records, and journal entries to spot patterns that are easy to miss in a short visit.`

Card 1
- Title: `Not a black box`
- Body: `Shows why it made a prediction.`

Card 2
- Title: `Built for longitudinal care`
- Body: `Looks at what changes across time.`

Card 3
- Title: `Designed for partnership`
- Body: `Helps patients and clinicians work from the same picture.`

- Primary CTA: `Continue`
- Link: `Explore how the model works`

### Interaction
- Continue -> Image 4
- Explore how the model works -> optional explainer drawer or page

### Notes for Figma
- Cards should feel like premium proof modules, not marketing tiles.
- Use subtle line icons only if necessary.

---

## Image 4 - Proof / outcomes
### Purpose
Show that the product is real, sophisticated, and useful without overwhelming the user.

### Design elements
- Back button top-left
- Headline and body left-aligned
- One featured proof card
- One supporting insight card
- Quiet CTA

### Text
- Headline: `Built to see what symptoms alone can miss.`
- Body: `In autoimmune disease, our model can surface rising flare-risk patterns across time and show the signals behind the prediction.`

Featured proof card
- Eyebrow: `Example`
- Title: `Autoimmune flare prediction`
- Body: `For one psoriatic arthritis case, the model identified rising flare-risk across the next 90 days and showed why.`
- Footer line: `Prediction with explanation, not a black box.`

Supporting card
- Title: `Journal intelligence matters too`
- Body: `Journal entries can reveal context, including when stress or symbolic distress may be amplifying a flare picture.`

Bottom line text
- `From guesswork to a clearer, more proactive plan.`

- Primary CTA: `Continue`

### Interaction
- Continue -> Image 5

### Notes for Figma
- Do not make statistical claims gigantic.
- This screen should feel like quiet authority, not chest-thumping.

---

## Image 5 - What should we call you?
### Purpose
Create a light personalization moment.

### Design elements
- Back button top-left
- Small oak mark centered above title
- Centered title and subheadline
- Single text field card
- Primary CTA at bottom

### Text
- Headline: `What should we call you?`
- Subheadline: `We’ll personalize your experience.`
- Input placeholder: `Your first name`
- Primary CTA: `Continue`

### Interaction
- Continue disabled until text entered
- Continue -> Image 6

### Notes for Figma
- Keep this warm but not cute.

---

## Image 6 - Diagnosed or searching
### Purpose
Let users self-identify the lens through which they enter the product.

### Design elements
- Back button top-left
- Small oak mark or oak glyph top-center
- Large title
- Short subheadline
- Two large selectable cards stacked vertically
- Small note below cards
- Bottom CTA

### Text
- Headline: `What brings you here today?`
- Subheadline: `We’ll tailor the experience to your situation.`

Card A
- Title: `I have a diagnosis`
- Body: `Track flares, patterns, and what helps.`

Card B
- Title: `I’m still searching for answers`
- Body: `Organize symptoms, patterns, and next steps.`

- Note: `You can change this later.`
- Primary CTA: `Continue`

### Interaction
- Selecting a card fills it subtly with soft sage/green tint and border accent
- Continue -> Image 7

### Notes for Figma
- The selected state should feel elegant, not loud.

---

## Image 7 - 30-day difficult-day map
### Purpose
Hook the user with a serious, analytical action that immediately feels relevant.

### Design elements
- Back button top-left
- Left-aligned title and instruction
- Optional helper row with small info icon
- Large elevated calendar card
- Calendar grid with last 30 days
- Difficult days shown as muted rust fills
- Flare days shown as muted rust fill plus darker ring
- Legend / counters below within same card or just below it
- Primary CTA anchored bottom

### Text
- Headline: `Let’s map the last 30 days.`
- Body: `Tap the days you felt significantly worse than your normal.`
- Helper: `Optional: long press to mark a flare day.`
- Counter 1: `Difficult days  8`
- Counter 2: `Flare days  2`
- Primary CTA: `Continue`

### Interaction
- Tap date = difficult day
- Long press date = flare day
- Continue disabled until at least one difficult day is marked
- Continue -> Image 8

### Notes for Figma
- This is one of the hero screens. Make it feel analytical and premium.
- Non-selected dates should still have subtle presence, perhaps thin stroke or soft typography.

---

## Image 8 - Top symptoms
### Purpose
Capture what matters most right now without making intake feel heavy.

### Design elements
- Back button top-left
- Title + subheadline
- Search field
- Suggested symptom chips
- Selected chip row
- Optional custom entry field
- Primary CTA bottom

### Text
- Headline: `What symptoms matter most right now?`
- Subheadline: `Pick up to 5. You can change this anytime.`
- Search placeholder: `Search symptoms`
- CTA: `Continue`

Suggested chip examples
- Fatigue
- Joint pain
- Brain fog
- Headaches
- Stiffness
- Poor sleep
- Anxiety
- GI issues

### Interaction
- User can select up to 5
- Continue -> Image 9

### Notes for Figma
- Chips should feel clean and medical, not playful.

---

## Image 9 - Why journaling matters
### Purpose
Teach the user why daily journaling/check-ins are powerful in this product.

### Design elements
- Back button top-left
- Oak symbol reduced in size or embossed watermark behind content
- Strong headline
- One clear body paragraph
- Three icon/bullet rows
- Subtle supporting proof card at bottom
- Primary CTA

### Text
- Headline: `Your journal helps us see more.`
- Body: `Symptoms alone rarely tell the whole story. Journaling helps us detect context, triggers, and patterns that can make your care plan clearer and more proactive.`

Bullet 1
- `Sleep and stress patterns`

Bullet 2
- `Symptom language and context`

Bullet 3
- `What may be driving a flare`

Supporting card
- Title: `Why this matters`
- Body: `More useful context for your doctor can mean fewer assumptions and a clearer plan.`

- CTA: `Continue`

### Interaction
- Continue -> Image 10

### Notes for Figma
- This screen should feel like a key product truth, not educational filler.

---

## Image 10 - Clarity goals
### Purpose
Ask what the user wants clarity on first so the app feels tailored.

### Design elements
- Back button top-left
- Title and short subheadline
- Multi-select checklist cards or chips
- Primary CTA bottom

### Text
- Headline: `What do you want clarity on first?`
- Subheadline: `Choose at least one. We’ll use this to focus your first pattern map.`

Options
- `What triggers my flares`
- `Whether stress or sleep is worsening symptoms`
- `Whether treatment is helping`
- `What to bring to my doctor`
- `What patterns repeat over time`

- CTA: `Continue`

### Interaction
- Multi-select allowed
- Continue enabled after one selection
- Continue -> Image 11

### Notes for Figma
- This replaces generic wellness categories with clinically meaningful focus.

---

## Image 11 - Build your first pattern map
### Purpose
Create a deliberate commitment to the first 3-day baseline.

### Design elements
- Back button top-left
- Centered headline
- Short body text
- One simple visual module showing 3-day baseline progression (Day 1, Day 2, Day 3)
- Optional subtle ring around oak icon as commitment symbol
- Primary CTA bottom

### Text
- Headline: `Build your first pattern map`
- Body: `Check in once a day for 3 days. We’ll start showing what changes, what repeats, and why.`
- Small proof line: `Not a black box. We show the signals behind the pattern.`
- CTA: `Start 3-day baseline`

### Interaction
- CTA -> Image 12

### Notes for Figma
- This is the behavioral commitment screen.
- Keep it elegant, not gamified.

---

## Image 12 - Save your map
### Purpose
Convert the invested user into an account holder.

### Design elements
- Back button top-left
- Title + subheadline
- Three account buttons stacked
- Small privacy line
- Legal links subtle at bottom

### Text
- Headline: `Save your map`
- Subheadline: `Create an account to keep tracking patterns over time.`
- Button 1: `Continue with Apple`
- Button 2: `Continue with Google`
- Button 3: `Continue with email`
- Trust line: `Private by design. You control what you share.`

### Interaction
- Account creation flow after selection
- Success -> Image 13

### Notes for Figma
- This should feel low-friction and trustworthy.

---

## Image 13 - Add records if you have them
### Purpose
Offer richer signal without blocking the user.

### Design elements
- Back button top-left
- Title + body
- Three upload option cards or buttons
- Secondary skip link
- Small privacy note

### Text
- Headline: `Add records if you have them`
- Subheadline: `Uploads can improve specificity sooner.`
- Button: `Upload PDF`
- Button: `Upload photo`
- Button: `Paste text`
- Secondary: `Skip for now`
- Trust note: `Encrypted in transit and at rest. You decide what to share.`

### Interaction
- Upload or skip -> Image 14

### Notes for Figma
- Upload flow must feel optional, not mandatory.

---

## Image 14 - Starting snapshot
### Purpose
Prevent Day 1 from ending abruptly and set intelligent expectations.

### Design elements
- Title + opening summary line
- Three concise cards or bullet modules
- One section titled “What happens next”
- Primary CTA
- Secondary advanced analysis link

### Text
- Headline: `Your starting snapshot`
- Summary line: `We have an early signal, but patterns sharpen with consistency.`

Three points
- `You marked 8 difficult days in the last 30 days.`
- `Top symptoms: fatigue, joint pain, brain fog.`
- `Your first 3 days will help reveal what changes, what repeats, and why.`

Section
- Header: `What happens next`
- Body: `To identify triggers, we look for repeat signals across sleep, stress, symptoms, meds, and records over time. We’ll ask only the questions that increase clarity.`

- Primary CTA: `Continue`
- Secondary link: `Advanced analysis`

### Interaction
- Continue -> Image 15

### Notes for Figma
- This is the first real feeling of value.

---

## Image 15 - Daily reminders
### Purpose
Set up the retention loop at the moment it makes sense.

### Design elements
- Back button top-left
- Title + body
- Simple reminder card showing a sample check-in notification
- Two option buttons or segmented selection for reminder timing
- Primary CTA and secondary link

### Text
- Headline: `Want a daily reminder?`
- Body: `A 2-second check-in helps patterns emerge faster.`
- Notification preview: `2OPMD  -  Ready to log today?`
- Primary CTA: `Enable reminders`
- Secondary: `Not now`

### Interaction
- Either choice -> Image 16

### Notes for Figma
- Do not overcomplicate reminder setup in onboarding.

---

## Image 16 - Add 2OPMD to your Home Screen
### Purpose
Encourage fast habit access.

### Design elements
- Back button top-left
- Title + body
- Mock widget preview with Oak icon, day streak, and “Log today” affordance
- Primary CTA and secondary link

### Text
- Headline: `Add 2OPMD to your Home Screen`
- Body: `One tap to log today and keep your pattern map moving.`
- Primary CTA: `Add widget`
- Secondary: `Maybe later`

### Interaction
- Either choice -> Image 17

### Notes for Figma
- Widget preview should look beautiful and useful, not gimmicky.

---

## Image 17 - First Home
### Purpose
Land the user in the real product with clarity and magnetism.

### Design elements
- Top section with Oak consistency module
- Small streak label and microcopy
- Three main cards max
- Collapsed timeline preview
- Two secondary action buttons at bottom of visible viewport
- Bottom tab bar

### Text
Oak module
- `Day 1 consistency`
- `Patterns strengthen with continuity.`

Card 1
- Title: `2-second check-in`
- Body: `Log today`

Card 2
- Title: `Patterns emerging`
- Body: `Not enough data yet. Check in for 2 more days to unlock your first pattern.`

Card 3
- Title: `Next step`
- Body: `Track sleep for 3 days to improve clarity.`

Buttons
- `Advanced analysis`
- `Prepare for visit`

### Interaction
- Check-in card -> Image 18
- Advanced analysis -> Image 20
- Prepare for visit -> Image 21

### Notes for Figma
- Home must feel calm, intelligent, and usable in 3 seconds.

---

## Image 18 - 2-second check-in
### Purpose
Make the daily habit effortless.

### Design elements
- Modal or full screen form
- Very minimal
- Slider 0-10
- Four optional toggles
- Primary save CTA

### Text
- Headline: `2-second check-in`
- Prompt: `How do you feel right now?`
- Toggles:
  - `Poor sleep`
  - `High stress`
  - `Missed meds`
  - `New symptom`
- CTA: `Save`

### Interaction
- Save -> Image 19

### Notes for Figma
- Keep this brutally simple.

---

## Image 19 - Post-save feedback / watering
### Purpose
Reward the behavior and reinforce the system.

### Design elements
- Brief overlay or transition state
- Small watering ripple around Oak or subtle droplet animation
- Short acknowledgment line
- Return to Home

### Text
- `Logged. Thank you.`
- Alternate state after enough data: `We’ll watch whether sleep aligns with symptom spikes.`

### Interaction
- Auto-return to Home

### Notes for Figma
- Watering is subtle and premium, not cute.

---

## Image 20 - Advanced analysis
### Purpose
Offer deeper value without overwhelming the default flow.

### Design elements
- Top nav
- Three meters or score modules: Consistency, Pattern clarity, Confidence
- One-sentence snapshot
- Evidence summary card
- “What improves accuracy” section
- Share with clinician CTA
- This is not medical advice note

### Text
- Headline: `Advanced analysis`
- Snapshot: `Current signal suggests difficult days may cluster after poor sleep.`

Module 1
- `Consistency`
- `3 of 3 baseline days logged`

Module 2
- `Pattern clarity`
- `Early signal forming`

Module 3
- `Confidence`
- `Moderate`

Evidence section
- Header: `What we used`
- Example list: `Daily check-ins, symptom map, stress tags, records if uploaded`

Accuracy section
- Header: `What improves accuracy`
- Example list: `More daily entries, medication list, sleep context, records`

Buttons
- `Share with clinician`
- `Explore how the model works`

Footer note
- `This is not medical advice.`

### Interaction
- Share -> Image 21 or native share flow

### Notes for Figma
- This is a premium analytics screen, not a dashboard circus.

---

## Image 21 - Prepare for visit
### Purpose
Convert insights into clinician-friendly utility.

### Design elements
- Intro screen with one short explanation
- Primary CTA to generate summary
- Secondary preview text below

### Text
- Headline: `Prepare for visit`
- Body: `Generate a one-page summary you can share with your clinician to make the visit more productive.`
- CTA: `Generate summary`

### Interaction
- Generate -> Image 22

### Notes for Figma
- This should feel useful and concrete, not flashy.

---

## Image 22 - Visit summary preview
### Purpose
Show the value of structured sharing.

### Design elements
- PDF-like summary preview card
- Sections stacked with labels
- Share / download / edit notes actions

### Text
Sections
- `What changed`
- `30-day map snapshot`
- `Top symptoms`
- `Notes to discuss`
- `Data confidence`

Buttons
- `Share`
- `Download PDF`
- `Edit notes`

### Interaction
- Download PDF may be locked for free users depending on monetization decision

### Notes for Figma
- Make this feel polished enough that a patient would be proud to show it.

---

## Image 23 - Day 3 pattern detected
### Purpose
Introduce monetization at the exact moment of felt value.

### Design elements
- Modal sheet or premium interstitial
- One short real insight
- Small Pro tease panel
- Two clear actions

### Text
- Headline: `First pattern detected`
- Insight: `Your difficult days appear to cluster after poor sleep.`

Pro tease
- Header: `Go deeper with Pro`
- Bullets:
  - `Advanced trigger mapping`
  - `Longer-horizon insights`
  - `Clinician-ready PDF export`

Buttons
- `Start 7-day free trial`
- `Continue with basic mode`

### Interaction
- Trial -> Image 24
- Basic mode -> Home

### Notes for Figma
- Calm and premium. No pressure tactics.

---

## Image 24 - How the free trial works
### Purpose
Reduce anxiety and increase conversion through clarity.

### Design elements
- Close icon top-left
- Title + reassuring subline
- Vertical timeline with 3 steps
- Primary CTA
- Small price / legal line at bottom

### Text
- Headline: `How your free trial works`
- Subhead: `Nothing will be charged today.`

Timeline
- `Today - Start with full access`
- `Before trial ends - We’ll remind you`
- `After trial - Continue or cancel anytime`

- Primary CTA: `Try for free`
- Legal microcopy: `Cancel anytime.`

### Interaction
- Try for free -> purchase flow

### Notes for Figma
- Borrow the behavioral clarity from the reference app, but make the copy feel grown-up and medically serious.

---

## Image 25 - Pro paywall
### Purpose
State the premium offer calmly and clearly.

### Design elements
- Title, subheadline, plan selector, benefit bullets, CTA
- White background, premium spacing
- No giant discount gimmicks

### Text
- Headline: `Unlock advanced analysis`
- Subhead: `Built to extend the conversation between appointments with organized, trackable data.`

Benefits
- `Deeper trigger mapping`
- `Longer-horizon pattern views`
- `Clinician-ready PDF export`
- `More detailed evidence summaries`

Plans
- `Annual  -  $199.99 / year`
- `Monthly  -  $19.99 / month`

- Primary CTA: `Start 7-day free trial`
- Secondary: `Continue with basic mode`
- Microcopy: `Cancel anytime.`

### Interaction
- Purchase or dismiss

### Notes for Figma
- Make it feel like a premium health service, not a consumer growth hack.

---

## Optional later visual world expansion
### Garden layer
- The broader garden metaphor can be introduced later in Home or weekly review.
- The Oak remains the main symbol.
- Journaling “waters” the system.
- A subtle sense of a growing grove or environment could emerge only after repeated use.
- Do not introduce Eden, biblical symbolism, or a named guide.

---

## What to borrow from the reference app
- One-screen-one-job onboarding flow
- Strong forward momentum
- Commitment screen
- Reminder setup
- Widget setup
- Trial explanation sequencing

## What to reject from the reference app
- Candle mascot
- Beige self-help tone
- Affirmation categories
- Relationship status or generic demographic detours
- “That’s it from me” personality-driven guidance
- Any framing that makes 2OPMD feel soft, vague, or unserious

---

## Figma build order
1. Global tokens
2. Typography styles
3. Buttons, cards, chips, calendar cells
4. Images 1 through 8
5. Images 9 through 16
6. Images 17 through 25
7. Empty / loading / error / locked states
8. Handoff frame for Rork / Dylan

---

## Final design north star
This should feel like:
- Apple Health meets Stripe meets a premium medical device
- clinically serious but emotionally safe
- elegant enough to feel expensive
- clear enough to feel inevitable
- intelligent enough to stand out immediately

