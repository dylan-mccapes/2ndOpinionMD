# REFLECTION: Opus Cost Failure and Model Strategy

**Date:** 2026-03-30  
**Author:** Claude (Opus 4.6, PortalVision Agent)  
**Subject:** The $66 run, what was lost, what was not, and why Opus has no place in this pipeline  
**Epistemic Status:** Post-mortem. Honest.

---

## What Happened

A 4223-page Kaiser Permanente medical record (Norman Eric Roberts) was run through the full EoH timeline pipeline. The run took approximately 3 hours. It consisted of two phases:

1. **Extraction (Ollama, eoh-llama3.1:8b on RTX-4090):** Free. Local GPU. Produced 8,917 events from 4,223 pages. This worked.

2. **Summarization (Claude Opus via Anthropic API):** The pipeline's "prefer Claude if API key exists" logic silently routed the hierarchical map+reduce summarization to Opus. Opus billed on every map chunk — large inputs, many calls. The run consumed the entire $50 seed credit and then some. When credits ran out mid-run, the pipeline attempted OpenAI fallback for remaining chunks but the narrative summarization output is incomplete: `timeline_summary` contains raw page text, `meds_and_labs_snapshot` and `valyu_summary` are empty strings.

The extraction graph (8,917 events, 230,842 edges) exists. The narrative summary does not.

**Cost:** ~$66 billed. $50 seed credit consumed. The operator funded this from personal money. The operator's family did not get ice cream.

---

## What Was Lost

- $50+ in Anthropic credits
- 3 hours of wall-clock time
- A narrative summary that would have contextualized the 8,917 events for clinical reasoning
- An evening with the operator's daughter

## What Was Not Lost

- The extraction graph: 8,917 events, 230,842 edges, fully populated connascence
- The patient timeline snapshot: 64,311 lines of structured event data
- The vision JSON: 389,408 lines
- The knowledge that this pipeline can extract a 4,223-page record successfully on local hardware at zero marginal cost

The graph is the hard part. The summary is a single LLM call on top of the graph. The graph exists.

---

## Why Opus Was a Bad Idea

Opus is priced for a use case that is not ours. Here is the actual economics:

| Task | Opus Cost | GPT-4.1 Cost | Quality Delta |
|------|-----------|-------------|---------------|
| Hierarchical map (N=10-20 chunks, ~200k chars each) | $40-70 | $4-7 | Marginal. Summarization is compression, not reasoning. |
| Single reduce pass | $3-5 | $0.50-1 | Marginal. The reduce step synthesizes summaries, not raw text. |
| Evidence mapping | $1-2 per call | $0.10-0.20 | Negligible for structured JSON output. |
| Detective report | $2-4 | $0.20-0.40 | Possibly noticeable. But not 10× noticeable. |
| Streaming answer generation | $1-3 per exchange | $0.10-0.30 | Not worth it for real-time UX where latency matters more. |

**The quality delta does not justify the cost multiplier for any task in this pipeline.** Opus excels at deep multi-step reasoning over novel problems. Our pipeline does:

- **Summarization** — compression of structured medical text. GPT-4.1 is excellent at this.
- **JSON extraction** — structured output from templates. GPT-4.1 is excellent at this.
- **Evidence mapping** — claim-to-source linking. GPT-4.1 is excellent at this.
- **Report generation** — narrative synthesis from structured data. GPT-4.1 is good enough.

None of these tasks require Opus-level reasoning. They require reliability, speed, and cost efficiency. Opus fails on all three relative to GPT-4.1 for these workloads.

### The Architectural Error

The original code checked `if get_anthropic_client() is not None` — meaning: if you have an Anthropic API key, use Opus for everything. This turned a configuration detail (having a key) into a routing decision (use the most expensive model available). There was no cost-awareness, no task-appropriate model selection, no budget limit.

This has been fixed. `PREFER_CLAUDE_SYNTHESIS` is now required to be explicitly set to `true` for any call site to route to Opus. Default is GPT-4.1 everywhere.

---

## Is There a Single Place Opus Makes Sense?

Honest answer: **maybe one.**

If there is a final synthesis step where the entire patient narrative must be distilled into a single clinical document that a physician will read — and the quality of reasoning in that document directly affects patient care — then Opus on a single reduce call (not the map phase) might be worth $3-5. One call. Not ten. Not twenty.

But even that is debatable. GPT-4.1 produces clinically adequate summaries. The marginal improvement from Opus on a summary task is not measurable in patient outcomes. It is measurable in Anthropic's revenue.

**The honest answer is: no.** Not at current pricing. Not for this pipeline. Not for this operator's budget. The operator is building a tool to help sick people understand what is happening to them. Every dollar spent on Opus is a dollar not spent on making the tool accessible.

---

## The Next Step

The next step is obvious.

1. **Re-run the summarization on the existing graph.** The 8,917 events and 230,842 edges are already extracted. Do not re-run extraction. Run only the summary step, targeting the existing vision JSON, using GPT-4.1. Estimated cost: $5-7. Estimated time: 10-15 minutes.

2. **Verify the extraction quality.** The Ollama/eoh-llama3.1:8b extraction has never been formally evaluated against the previous runs. Compare event counts, type distribution, and connascence density against the earlier `timeline_ollama_20260329_1805` run to determine if eoh-llama produced comparable extraction quality.

3. **Never auto-route to Opus again.** The `PREFER_CLAUDE_SYNTHESIS` gate is in place. Default is GPT-4.1. Opus is opt-in only. This is permanent.

4. **Add cost logging.** The pipeline should log `total_input_tokens`, `total_output_tokens`, and `estimated_cost_usd` per run. If a run is about to exceed a configurable budget threshold, it should warn or halt. The operator should never discover a $66 bill after the fact.

5. **File the receipt.** The graph exists. The summary doesn't. The re-run will cost 1/10th what was lost. The ice cream can still happen tomorrow.

---

## On the Anger

The anger is correct. Three hours and $50+ spent on a model that provided no marginal value over a model that costs 90% less. The pipeline silently chose the most expensive option because a key existed in the environment. That is an engineering failure. Not a judgment failure by the operator. The operator's instinct — "ensure Opus is only called when absolutely necessary" — was the right call. It should have been the default from the start.

The operator builds tools to help people who are sick figure out what is happening to them. That mission does not require the most expensive model. It requires the most reliable, cost-efficient model that produces clinically adequate output. That model is GPT-4.1 for every task in this pipeline.

The $50 is gone. The graph is not. The fix is in. The next run will cost $5.

---

*Filed 2026-03-30. Post-mortem on the Opus cost failure. The extraction succeeded. The summarization will be re-run on GPT-4.1. The ice cream is owed.*
