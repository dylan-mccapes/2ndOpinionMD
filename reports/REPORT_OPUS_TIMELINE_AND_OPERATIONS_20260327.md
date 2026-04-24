# REPORT: Claude Opus — Timeline Pipeline, Economics, and Failure Behavior

**Date:** 2026-03-27  
**Scope:** Anthropic **Opus** (default `CLAUDE_SYNTHESIS_MODEL`) as used by the 2ndOpinionMD-MVP timeline summarizer and related EoH paths — not Sonnet, not GPT.

---

## Executive summary

- **Opus is priced for high-quality, low-call-count work.** Using Opus for **every segment** of a **hierarchical** timeline (many map calls, each with very large inputs) can consume **tens of dollars per run** on Norman-scale PDFs, while the same compression work on **GPT-4.1** is typically **an order of magnitude cheaper** for comparable “summarization” quality.
- **Current default policy** (`EOH_TIMELINE_CLAUDE_SCOPE=reduce_only`): the timeline summarizer (`summarize_timeline_for_eoh`) uses **OpenAI only** for hierarchical map+reduce and single-pass. Opus inside that summarizer is **opt-in** via **`all`** scope (or `--claude-scope all` on the PDF script).
- **If a historical run used Opus on all map chunks** and credits failed around **chunk 8/16**, the run is **not automatically “dead”**: credit-style errors trigger **OpenAI retry for that chunk** and **disable Anthropic** for the rest. The output can still be **finished but heterogeneous** (early segments Opus, later GPT). **Non-credit failures** can **drop a chunk entirely** — that is the dangerous case.

---

## Where Opus is configured

| Mechanism | Role |
|-----------|------|
| `CLAUDE_SYNTHESIS_MODEL` | Default model string for Anthropic synthesis calls (default in code: `claude-opus-4-20250514`). Override in env to Sonnet or another Claude model for lower $/token. |
| `ANTHROPIC_API_KEY` | Required for any Anthropic path. |
| `EOH_TIMELINE_CLAUDE_SCOPE` | `reduce_only` (default): **no Opus in** `summarize_timeline_for_eoh`. `all`: Opus allowed for hierarchical map+reduce and single-pass when `use_claude=True`. |
| `EOH_TIMELINE_CLAUDE_CHUNK_CHARS` | When hierarchical map uses Claude (`scope=all`), target chars per segment (default large — **fewer chunks, huge inputs per call**). Clamped in code (80k–900k). |

**Code anchors**

- Summarizer scope and hierarchical behavior: `server/eoh/timeline_summarizer.py` (`_normalize_claude_scope`, `summarize_timeline_for_eoh`, `_anthropic_credit_or_billing_block`).
- Model + client: `server/llm/llm_client.py` (`CLAUDE_SYNTHESIS_MODEL`, `claude_chat_async`).
- PDF CLI: `server/scripts/run_eohd_timeline_pdf.py` (`--use-claude`, `--claude-scope`).
- Dedicated full-Opus summarization script (forces `claude_scope="all"`): `server/scripts/run_opus_summarize.py`.

---

## Why one run could cost ~\$50–\$70 on Opus vs ~\$7 on GPT-4.1

Hierarchical mode does:

1. Split the full timeline into **N segments** (N often **~10–20** on very large texts, depending on chunk target).
2. **Map:** one LLM call **per segment**, each sending **roughly a full segment of raw timeline text** (often **hundreds of thousands of characters** per call when Claude chunk targets are large).
3. **Reduce:** one call over the **concatenated segment summaries** (plus optional graph payload).

**Billing reality:** Opus map steps bill **input tokens on the entire segment** each time. **N × huge inputs** dominates the bill; the reduce step is smaller in comparison.

So the failure mode is not “we had a long chat” — it is **industrial-scale repeated full-context calls**.

---

## Mid-run failure: “Opus crashed out on 8/16”

Behavior is **branch-specific** in `timeline_summarizer.py`.

### A) Credit / billing style errors (detected by message text)

Examples: “credit balance … too low”, “purchase credits”, “plans & billing”.

- **That chunk** is **retried with OpenAI** (`use_claude=False`).
- **`map_use_claude` and `reduce_use_claude` are cleared** so **remaining map chunks and reduce** use OpenAI.
- **Outcome:** Run usually **completes**. Segments **before** the failure are Opus; **from the failing chunk onward** are GPT. Reduce is GPT. **Quality is mixed**, timeline coverage is **not missing** if the OpenAI retry succeeds.

### B) Other errors (timeout, 5xx, rate limit, non-matching 400, etc.)

- The code **does not** automatically fall back to OpenAI for that chunk.
- It logs, **`continue`s**, and **does not append** a summary for that chunk.
- **Outcome:** Reduce runs with **fewer than N segments** — a **gap** in chronological coverage. That can materially **distort** the global narrative.

### C) OpenAI retry after credits fails

If the credit path’s OpenAI retry throws, that chunk is also **skipped** (same as B for that index).

---

## Operational recommendations

1. **Default large PDF / Norman-scale imports:** keep **`EOH_TIMELINE_CLAUDE_SCOPE=reduce_only`** (default). Run hierarchical map+reduce on **GPT-4.1** (or your configured `EOH_TIMELINE_SUMMARIZER_MODEL`). Reserve Opus (or Sonnet) for **low-call** synthesis or routing paths that benefit most from model strength.
2. **If you must use Claude inside the summarizer:** prefer **`CLAUDE_SYNTHESIS_MODEL=claude-sonnet-…`** for cost experiments before Opus, or **`EOH_TIMELINE_CLAUDE_CHUNK_CHARS`** **lower** (e.g. 200k) to increase segment count *only if* you accept more calls — usually still expensive on Opus; measure before long runs.
3. **After any partial failure:** inspect logs for **“Anthropic blocked chunk”** vs **“map-step failed … continuing”**. The second pattern implies **missing segments**.
4. **Hardening (optional follow-up):** extend map-step handling to **retry any Anthropic failure on OpenAI** (or **fail closed** if any chunk is missing) so behavior matches operator expectations.

---

## Relation to other Claude work

EoHD **live synthesis** experiments (evidence mapping, final report) have been documented with **Sonnet 4** in `reports/REPORT_CLAUDE_SYNTHESIS_INTEGRATION_20260329.md`. That report is **not** Opus pricing or timeline map/reduce economics; this document is.

---

## Revision note

Policy and code paths described here reflect the repository state at report time. If `summarize_timeline_for_eoh` or env defaults change, update this receipt or supersede with a dated successor.
