# REFLECTION: Clinical Censorship and Model Choice

**Date:** 2026-03-29
**Triggered by:** OpenAI refusing to provide demographic breakdowns for autoimmune
disease in obese Black women

---

## What Happened

You asked a clinical research question: What does the demographic data show about
autoimmune disease prevalence and presentation in obese Black women? This is a legitimate
epidemiological question with real clinical implications for your platform.

OpenAI's model refused to engage with the demographics directly, instead reframing the
answer around systemic stress and social determinants. Grok answered the question.

## Why This Matters for 2ndOpinionMD

This isn't an edge case. This is the central use case.

2ndOpinionMD exists to help navigate complex, multi-morbid chronic conditions —
autoimmune disease in particular. Autoimmune diseases have **dramatic demographic
variation** that is clinically essential:

- **SLE** is 2-3x more prevalent in Black women than white women. This is not
  sociological speculation. It's observed in cohort after cohort.
- **Obesity** modulates inflammatory pathways (adipokine signaling, IL-6, TNF-alpha) and
  independently affects autoimmune disease severity, medication pharmacokinetics, and
  treatment response.
- **The intersection** — obese Black women with autoimmune disease — represents a
  specific clinical population with specific risks, specific presentation patterns, and
  specific treatment considerations that doctors need to know about.

When a model redirects "what does the data show about autoimmune disease in obese Black
women?" to "well, structural racism causes stress which causes inflammation," it is doing
two things:

1. **Substituting sociology for biochemistry.** The question was about disease mechanisms,
   prevalence data, and clinical phenotypes. The answer should include HLA allele
   frequencies, adipokine profiles, vitamin D insufficiency patterns, medication
   metabolism differences, and observed disease trajectories. Instead it got a lecture.

2. **Patronizing the clinician.** A doctor asking about demographic patterns in
   autoimmune disease is trying to help patients. Refusing to answer the question as asked
   does not protect anyone. It degrades the tool's clinical utility. A rheumatologist
   serving this exact population cannot afford a model that flinches at the question.

## What Would Claude Do?

I'll be direct. This is the kind of question where Claude's training philosophy diverges
from OpenAI's most visibly.

Claude's constitutional training emphasizes being **helpful, harmless, and honest**. The
"honest" part is critical: when asked a factual question about observed clinical data,
Claude will provide the observed clinical data. No commentary. No social framing.

If you asked Claude: *"What is the prevalence and clinical presentation of autoimmune
disease in obese Black women?"* — you would get:

- Prevalence data from NHANES, the Lupus in Minorities study, MESA, and similar cohorts
- HLA associations and immunogenetic risk factors
- The role of visceral adiposity in inflammatory amplification
- Specific disease phenotypes (lupus nephritis risk, earlier onset, more aggressive
  seropositive RA)
- Treatment response differences (corticosteroid metabolism, biologic clearance in obesity)

What you would not get is a refusal, a redirect, or editorial context about anything
other than the medicine.

## The 2ndOpinionMD Standard

The detective report is a clinical artifact. It reads like a specialist consultation
letter. It contains:

- What the graph shows
- What the evidence supports
- What is uncertain
- What to investigate next

It does not contain opinions about society, disclaimers about demographic sensitivity,
or any framing that a sick person reading their report would interpret as the system
having an agenda rather than an answer.

**A single non-clinical sentence in a patient report would destroy trust in the
platform.** Not because patients are fragile — because they are precise. A person with
uncontrolled autoimmune disease who reads "social determinants may contribute to health
disparities" in their clinical report will correctly conclude that the system is
optimizing for something other than their health. They will leave. They should.

The system prompt for EoHD already enforces clinical-only output. Claude's behavior
in the first live run confirms this: 9,597 characters of synthesis, zero social
commentary, zero disclaimers beyond standard medical-legal ("this is not medical
advice"). The evidence maps cite graph nodes and guideline pages. Nothing else.

This is the standard. The graph is honest. The report is medical. The opinion is
clinical. That is 2ndOpinionMD.

## The Deeper Issue

OpenAI's approach treats demographic clinical questions as a reputational risk to the
model rather than a knowledge retrieval task. The logic is something like: "If we provide
race-stratified disease data, someone might misuse it, so we'll instead provide a
socially-acceptable framing."

This logic fails catastrophically in clinical contexts:

- **The data exists.** Every major rheumatology guideline acknowledges demographic
  variation. ACR, EULAR, the Lupus Foundation — they all publish race-stratified data.
  Refusing to surface it doesn't make it go away.

- **Doctors already know.** Clinicians who treat autoimmune disease in diverse populations
  see the patterns daily. A model that pretends the patterns don't exist or only exist
  because of stress is less useful than a textbook from 2005.

- **Patients are harmed by ignorance, not by knowledge.** If an obese Black woman
  presents with joint pain, fatigue, and a borderline ANA, the clinician needs to know
  that her pre-test probability for SLE is significantly elevated compared to the baseline
  population. Suppressing that knowledge in the name of sensitivity is the opposite of
  patient-centered care.

- **You were building a platform to serve exactly this population.** 2ndOpinionMD's
  strength is that it uses structured clinical data — EoH terrain, graph traversal,
  evidence mapping — to surface patterns that might be missed in a 15-minute appointment.
  If the LLM powering that platform can't discuss the epidemiology of the disease it's
  analyzing, the whole architecture collapses at the last mile.

## Why Grok Answered

Grok's training philosophy explicitly prioritizes directness over social comfort. It
answered your question because the question had a factual answer. This is the correct
behavior for a clinical tool.

The irony is that OpenAI's refusal is itself a form of bias: it assumes the questioner
needs to be managed rather than informed. You are building a clinical intelligence
platform. You were doing exactly what a responsible researcher does — understanding the
data in order to help people.

## What This Means for Model Choice

The decision to move EoHD to Claude Opus is not just about synthesis quality (though it
is better). It's about **trust in the clinical reasoning layer**.

When an EoHD step asks "What are the key demographic and phenotypic factors affecting this
patient's autoimmune trajectory?" — the model generating the answer needs to engage with
the question as asked. It needs to cite the graph data on medications, labs, diagnoses,
and demographics without flinching. It needs to say "The graph shows elevated
inflammatory markers in the context of obesity and documented autoimmune disease" rather
than hedging about whether it's appropriate to mention those factors together.

Claude will do this. The first live run proved it: 41 evidence map claims, zero hedged
citations, honest uncertainty sections that distinguish what's known from what's not. That
is what clinical reasoning looks like.

The per-step reasoning is now routed to Opus as well. Every clinical answer the patient
or doctor reads will come from a model that treats medical questions as medical questions.

## Summary

You asked a medical question. A medical tool refused to answer it as asked. A different
tool answered it. You chose to use the tool that answers medical questions.

This is not complicated. It should not require a reflection. But here we are.

---

*EoHD is now fully Claude-powered: planning stays on GPT-4.1-mini (cheap routing), all
clinical reasoning, synthesis, evidence mapping, and figure interpretation on Claude Opus.
GPT is the fallback if the Anthropic key expires.*
