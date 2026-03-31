# Complaint: Claude Opus API Billing — $66 Charged, Zero Usable Output

**Date:** 2026-03-30
**From:** Dylan McCapes — 2ndOpinionMD / PortalVision
**To:** Anthropic Support — support@anthropic.com
**Model:** claude-opus-4-20250514
**Estimated billing:** ~$66 USD
**Seed credit consumed:** $50 (initial Anthropic API credit)
**Usable output received:** None

**Subject line for email:** Refund Request — Claude Opus API, ~$66 billed for zero usable output (claude-opus-4-20250514)

---

## Summary

On March 30, 2026, I ran a medical record summarization pipeline through the
Claude Opus API (claude-opus-4-20250514). The pipeline processed a 4,223-page
Kaiser Permanente medical record using hierarchical map+reduce summarization —
approximately 10-20 API calls, each with large input payloads (hundreds of
thousands of characters per call).

The run consumed my entire $50 seed credit and incurred approximately $16 in
additional charges (~$66 total) over approximately 3 hours. **The output was
completely unusable.** The primary summary field contains raw, unprocessed page
text from the PDF — not a narrative summary. The medications/labs and clinical
signal fields are empty strings.

An equivalent run on GPT-4.1 costs $5-7 and produces clinically adequate output.

---

## What Happened

1. **Pipeline:** My application (2ndOpinionMD) processes patient medical records
   to help sick individuals understand their clinical history. The pipeline
   extracts events from PDF pages using a local LLM (Ollama, zero cost), then
   runs narrative summarization through a cloud API.

2. **Opus routing:** Due to an application-level configuration issue (now fixed),
   the summarization was routed to Claude Opus instead of GPT-4.1. This is my
   engineering error — I accept responsibility for the routing decision.

3. **What Opus was asked to do:** Summarize chronological segments of a medical
   timeline into structured JSON (timeline narrative, medications/labs snapshot,
   clinical signal terms). This is a compression task, not a complex reasoning task.

4. **What Opus produced:** The `timeline_summary` field in the final output
   contains verbatim raw page text from the PDF (pages 1-20 of the record,
   including demographics, immunization records, and implant serial numbers).
   The `meds_and_labs_snapshot` field is an empty string. The `valyu_summary`
   field is an empty string. **None of the requested structured summarization
   was performed.**

5. **Credit exhaustion mid-run:** The $50 seed credit was consumed partway
   through the hierarchical map phase. The pipeline detected the credit
   exhaustion and attempted OpenAI fallback for remaining chunks, but the
   overall output was corrupted — early Opus chunks produced no usable summaries,
   and the reduce step operated on incomplete/malformed intermediate results.

6. **Contributing factor — output token limit:** Upon post-mortem investigation,
   I discovered that the API call was configured with `max_tokens=4096` for the
   output. For a hierarchical reduce step over a 4,223-page medical record, 4096
   output tokens is insufficient to produce a meaningful clinical narrative. This
   is my application's bug, but it does not explain why the model returned raw
   input text as output rather than a truncated summary.

---

## The Output Evidence

The final `timeline_summaries_export.json` file (preserved in my artifact
directory) shows:

- `timeline_summary`: Begins with "=== Page 1 === Release of Medical
  Information 25 N Via Monte Walnut Creek, CA 94598 ..." — this is the raw
  PDF text, not a summary. It continues for approximately 41,000 characters
  of unprocessed medical record pages.
- `meds_and_labs_snapshot`: `""` (empty string)
- `valyu_summary`: `""` (empty string)

The graph extraction (8,917 events, 230,842 connascence edges) was performed
by a local Ollama model at zero API cost and is intact. Only the Opus
summarization failed.

---

## What I Am Requesting

1. **Credit or refund for the failed run.** I was billed approximately $66 for
   API calls that produced zero usable output. The model did not perform the
   requested task (structured summarization) — it returned raw input text. I
   acknowledge the routing was my application's error, but the output quality
   is not consistent with a functioning model. A model that returns its input
   verbatim as its output has not performed work.

2. **Transparency on what happened.** If the model encountered an internal
   error, context overflow, or output constraint that caused it to fall back
   to echoing input text, that should be surfaced as an error response — not
   billed as a successful completion. I have no way to distinguish "model
   performed work and produced output" from "model echoed input" without
   inspecting every response, which defeats the purpose of automation.

---

## Context

I am an independent researcher building 2ndOpinionMD — a tool to help patients
with complex medical histories understand their clinical trajectories. This is
not a funded company. The $50 seed credit represented my initial investment in
evaluating Anthropic's API for this use case. The additional $16 came from
personal funds.

The run was intended to summarize the medical record of a real patient (with
consent) to demonstrate the system's capability. Instead, I lost 3 hours of
compute time, $50+ in credits, and an evening with my family. The patient
received no benefit.

I have since re-architected the pipeline to default to GPT-4.1 for all tasks,
with Opus gated behind an explicit opt-in environment variable
(`PREFER_CLAUDE_SYNTHESIS=true`). Opus will not be used in production.

---

## Artifacts Available Upon Request

- `timeline_summaries_export.json` — the final output showing raw text in the
  summary field and empty strings in other fields
- Application logs from the run showing the sequence of API calls
- The pipeline source code showing the `max_tokens=4096` configuration and
  hierarchical map+reduce call pattern
- The corrected code with the `PREFER_CLAUDE_SYNTHESIS` gate

---

**Dylan McCapes**
2ndOpinionMD / PortalVision
Independent researcher — Berkeley, CA
