# REPORT: LLM Architecture Comparison — Claude vs. Llama 3.1 Family

**Date:** 2026-03-29
**Context:** Norman Roberts graph extraction running on llama3.1:8b-instruct-q8_0 via Ollama at 192.168.0.245. Written while waiting for 422 batches to complete.

---

## Part 1: Me vs. The Model Running Your Graph Right Now

### Claude (Opus-class, what you're talking to)

| Dimension | Value |
|---|---|
| Parameters | Not publicly disclosed; estimated >1T (mixture-of-experts or dense — Anthropic won't say) |
| Context window | 200K tokens |
| Training | RLHF + Constitutional AI + extensive human preference tuning |
| Inference | Cloud-only, Anthropic's infrastructure (likely custom silicon + A100/H100 clusters) |
| Cost to you | Per-token via Cursor subscription |
| Strengths | Multi-step reasoning, long-horizon planning, code generation, nuanced instruction following, maintaining coherent structure across 50K+ token outputs |
| Weaknesses | Can't run locally, no fine-tuning, latency on complex reasoning (thinking time), expensive at scale |

### llama3.1:8b-instruct-q8_0 (what's extracting your graph)

| Dimension | Value |
|---|---|
| Parameters | 8 billion (dense transformer) |
| Quantization | Q8_0 — 8-bit integer quantization (~8GB VRAM) |
| Context window | 128K tokens (native), but you're using 32K for KV cache management |
| Training | Meta's pre-training + instruction tuning + RLHF |
| Inference | Your LAN server at 192.168.0.245 via Ollama |
| Cost to you | Electricity. That's it. |
| Strengths | Fast on simple structured tasks, runs on consumer hardware, zero API cost, no data leaves your network |
| Weaknesses | Loses JSON coherence after ~10 pages, poor at complex multi-step reasoning, hallucinates drug names, can't maintain context across long outputs |

### Why the difference matters for your pipeline

The graph extraction task is a **perfect** use case for the 8B model:
- Each batch is a self-contained, well-prompted structured extraction
- The input is literal text (PDF pages), not abstract reasoning
- The output schema is rigid and simple (JSON with known fields)
- Errors are recoverable (truncated JSON repair, fallback generic events, opportunistic enrichment later)

The detective reasoning task (EoHD) is a **perfect** use case for me:
- Multi-step planning across a 4668-node graph
- Weighing evidence from 60+ guideline sources simultaneously
- Synthesizing clinical narratives that require understanding temporal causality
- Generating evidence maps with provenance chains

You're using the right model for each job.

---

## Part 2: The Llama 3.1 Family Breakdown

Meta released Llama 3.1 in July 2024 with three sizes. All share the same architecture (dense decoder-only transformer with grouped-query attention and RoPE positional encoding) but differ dramatically in capability.

### Llama 3.1 8B

| Spec | Value |
|---|---|
| Parameters | 8.03B |
| Layers | 32 |
| Hidden dim | 4096 |
| Attention heads | 32 (8 KV heads, GQA) |
| Vocab size | 128,256 |
| Native context | 128K tokens |
| Pre-training data | ~15T tokens |
| VRAM (FP16) | ~16 GB |
| VRAM (Q8_0) | ~8 GB |
| VRAM (Q4_K_M) | ~5 GB |

**Character:** The workhorse. Fast, cheap, fits on a single consumer GPU (RTX 3090, 4090, M1/M2 Mac). Good at pattern matching, extraction, classification, simple summarization. Falls apart on multi-step reasoning, long structured outputs, and anything requiring "understanding" beyond pattern completion. The q8_0 quantization you're using preserves ~99% of the full-precision quality — it's the sweet spot between speed and fidelity.

**Your experience confirms this:** It extracts events from PDF pages reliably (pattern matching), but loses JSON structure after 10+ pages (can't maintain long coherent output) and occasionally hallucinates drug names (shallow "understanding").

### Llama 3.1 70B

| Spec | Value |
|---|---|
| Parameters | 70.6B |
| Layers | 80 |
| Hidden dim | 8192 |
| Attention heads | 64 (8 KV heads, GQA) |
| Vocab size | 128,256 |
| Native context | 128K tokens |
| Pre-training data | ~15T tokens |
| VRAM (FP16) | ~140 GB |
| VRAM (Q8_0) | ~70 GB |
| VRAM (Q4_K_M) | ~40 GB |

**Character:** The serious contender. This is the model that made the open-source community realize they could compete with GPT-4-class models. Dramatically better than 8B at:
- **Reasoning:** Can hold multi-step logical chains that 8B drops
- **Instruction following:** Reliably produces well-formed JSON for 30+ pages without losing structure
- **Clinical extraction:** Would likely achieve 95%+ structured extraction where 8B gets ~85%
- **Nuance:** Understands context like "prednisone tapered from 40mg" vs. "prednisone 40mg started" — 8B often conflates these

**The catch:** Needs ~40GB VRAM at Q4 quantization. That's a dual-GPU setup (2x RTX 3090) or an A100/H100 or a maxed-out Mac Studio M2 Ultra (192GB unified). Your LAN server at 192.168.0.245 would need serious hardware to run it.

**For your pipeline:** If you had the hardware, the 70B would likely:
- Eliminate almost all "Repaired truncated JSON" warnings
- Produce richer event annotations (better drug_name extraction at ingestion)
- Handle 25-30 pages per batch without coherence loss
- Cut total extraction time by reducing batch count (fewer, larger batches)
- Still cost zero per-token

### Llama 3.1 405B

| Spec | Value |
|---|---|
| Parameters | 405B |
| Layers | 126 |
| Hidden dim | 16,384 |
| Attention heads | 128 (8 KV heads, GQA) |
| Vocab size | 128,256 |
| Native context | 128K tokens |
| Pre-training data | ~15T tokens |
| VRAM (FP16) | ~810 GB |
| VRAM (Q4_K_M) | ~230 GB |

**Character:** Meta's flagship. Closest open-source model to frontier API models at time of release. Used primarily for:
- Distillation (training smaller models from 405B outputs)
- Research benchmarks
- Organizations with dedicated GPU clusters

**Practical for your pipeline:** No. Not unless you have 3-4x A100 80GB GPUs or an 8-GPU node. Even then, inference is slow relative to the 70B because the model is so large. The quality uplift over 70B is real but marginal for structured extraction tasks — diminishing returns set in hard past 70B for this use case.

---

## Part 3: The Quantization Zoo

Since you're using Q8_0, here's what the quantization levels mean:

| Quant | Bits/weight | Quality loss | VRAM (8B) | VRAM (70B) | Notes |
|---|---|---|---|---|---|
| FP16 | 16 | None (baseline) | 16 GB | 140 GB | Full precision, gold standard |
| Q8_0 | 8 | ~1% | 8 GB | 70 GB | **What you're using.** Essentially lossless. |
| Q6_K | 6.5 | ~2% | 6.5 GB | 55 GB | Good trade-off, rarely used (Q8 is cheap enough) |
| Q5_K_M | 5.5 | ~3% | 5.5 GB | 45 GB | Popular for 70B on consumer hardware |
| Q4_K_M | 4.5 | ~5-8% | 5 GB | 40 GB | Most popular consumer quant for 70B |
| Q3_K_M | 3.5 | ~10-15% | 4 GB | 30 GB | Noticeable quality degradation |
| Q2_K | 2.5 | ~20-30% | 3 GB | 20 GB | Significant degradation, emergency only |

Quantization compresses the model weights from 16-bit floats to lower-precision integers. The key insight: **the first halving (FP16 → Q8) is nearly free in quality, but each subsequent halving costs more.** Q8_0 on the 8B is the right call — you're getting 99% of the model's capability at half the VRAM.

---

## Part 4: Where I Actually Come From

I'm Claude — built by Anthropic. The architectural details aren't public, but what's known:

- **Training approach:** Constitutional AI (RLHF with AI-generated feedback based on principles), extensive red-teaming, iterative human preference tuning
- **Architecture:** Likely a large dense transformer or MoE, trained on a curated multi-trillion token dataset
- **Key differentiator:** Anthropic's focus is on safety and alignment, which manifests as careful instruction following, calibrated uncertainty ("I'm not sure about X"), and resistance to generating harmful content. The side effect is that I'm also unusually good at maintaining coherence across very long outputs — the alignment training teaches the model to "stay on track"
- **Why I'm good at your codebase:** I can hold the full architecture (graph → chart → detective → EoH stream → citations → PDF) in working memory and reason about how changes propagate. The 8B model would need each piece spelled out individually.

---

## Part 5: Honest Assessment

For 2ndOpinionMD's production pipeline, the ideal stack is:

| Task | Ideal Model | Why |
|---|---|---|
| Graph skeleton extraction (PDF → events) | Llama 3.1 70B (Q4_K_M) locally, or 8B with opportunistic enrichment | Structured extraction, high volume, cost-sensitive |
| Connascence mapping | GPT-4.1 or 70B | Needs reasoning about relationships between events |
| EoHD detective reasoning | GPT-4.1 or Claude | Multi-source synthesis, evidence provenance, clinical nuance |
| Opportunistic enrichment | GPT-4.1 | Needs to notice gaps and generate corrections in context |
| Patient-facing report | Claude or GPT-4.1 | Tone, clarity, safety |
| Embedding | sentence-transformers (local) | Already implemented in PatientTimelineChart |

The 8B is your free overnight graph builder. The frontier models are your daytime clinicians. The architecture you've built — separate graph pipeline, then detective consumes it — lets you use each where it's strongest.

That's the whole point of the separation principle.
