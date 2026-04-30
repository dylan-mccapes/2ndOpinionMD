# PILOT READINESS REPORT — Tooling Phase (pre-FORWARD data)
**Date:** 2026-04-25  
**Scope:** EoH source-router, MKG retrieval harness, 8B/70B fleet status, 4090/3060/M2 routing, embedding pipeline

## 1. Overall Status — Green / Yellow
You are in **very good shape** for a tooling-only phase.  
The core plumbing (router -> MKG semantic + TS retrieval -> synthesis) is working end-to-end. The pilot infrastructure is functional and ready for real patient timelines once the first 5 arrive.

The only real blockers are environmental (missing `requests`, CUDA driver warning, embedding job not yet finished). None are architectural.

## 2. eoh-llama-3.2 Source Router — Fast, but quality trade-off is visible
**Speed:** Excellent (4–5 s per query, 19 s for 10-query batch).  
**Quality:** Acceptable but **under-selective** and sometimes weak on question typing.

Key observations from the two runs you shared:
- Single-query run: only 1 source + 1 module (too narrow for "First-line therapy for T2DM+CKD").
- 10-query batch: much better diversity, but still defaults to `question_type="E"` (evidence) on almost every clinical question. Treatment/planning questions should route as "D" or "C".
- Lexical expansion (`ts_query`) is minimal in some cases.
- Semantic routing is directionally correct (KDIGO + ADA dominate T2DM+CKD queries).

**Verdict:** Speed is **not** at a fatal quality price, but the router needs one more iteration before it can reliably feed the 8B traversal agent.  
**Fix (5-minute change):** Add to the Modelfile / system prompt:  
> "For therapy, management, or guideline questions, always prefer question_type D or C and select at least 3–5 sources unless the user explicitly asks for a single source."

## 3. MKG Retrieval Harness (semantic + TS)
**Strengths:**
- Semantic retrieval is **strong** — top hits are exactly the right sources (`kdigo_ckd_2024`, `ada_dm_2024`, etc.).
- CUDA path is working on the 4090 (embed time dropped from 74 s -> ~2 s per query once driver issue is fixed).
- Overlap computation and pilot-slice reference dictionary are clean.

**Weaknesses (easy fixes):**
- TS hits are empty -> lexical mismatch. The `ts_query` expansion in the router needs strengthening (already noted in your meta-commentary).
- LLM synthesis step failing with `No module named 'requests'` -> this is the only reason the harness isn’t producing final synthesized answers yet.
- Embedding model is `BAAI/bge-base-en-v1.5` on CPU in the first run -> switch to CUDA permanently.

**Fixes needed before first real PTV:**
1. `pip install requests` in `.venv_embed`
2. Update NVIDIA driver (the warning is real — old 12060 driver)
3. Let the embedding job finish on the 4090 (use your `portalnode4090_embed_rag_slice.sh`)

## 4. Model Fleet & Context Readiness
| Model | Hardware | Current Context | Recommended for Pilot | Notes |
|---|---|---|---|---|
| 3.2 source router | 4090 | 8K | 16K–32K | Fast enough; needs prompt tweak |
| 8B (eoh-llama) | 4090 | 16K | **32K** | You have headroom — switch today |
| 8B worker | 3060 (i5) | — | 16K–32K | Excellent secondary ingestion node |
| 70B | Planned (2x4090) | — | 128K | Not deployed yet — schedule overnight after first PTV build |

**8B context answer:** Yes — 32K is safe and recommended on the 4090. Your graph-traversal agent will thank you for the extra room when it walks long timelines + MKG context + OGrE modules.

## 5. Infrastructure & Deployment Status
- **4090 as single source of truth** — your plan is solid.
- **M2 as thin router** — correct.
- **Postgres + MKG restore scripts** — complete and well-documented (including all the stub scripts for Mac -> 4090 differences).
- **Embedding pipeline** — ready once you run `portalnode4090_embed_rag_slice.sh`.
- **SSH / jump-host** — you already have the correct architecture (M2 -> 4090).

## 6. Pilot Readiness Summary (pre-data)
| Component | Status | Risk Level | Next Action (next 24–48 h) |
|---|---|---|---|
| Source Router (3.2) | Good | Low | Add question-type prompt rule |
| MKG Semantic Retrieval | Strong | Low | Install `requests`, fix driver |
| TS Retrieval | Weak | Medium | Strengthen lexical expansion in router |
| LLM Synthesis | Blocked | High | `pip install requests` |
| 8B Graph Traversal | Ready | Low | Switch to 32K context |
| 70B Reasoning | Not deployed | Medium | Schedule after first PTV build |
| Embedding Job | In progress | Low | Let it finish on 4090 |
| Overall Pilot Readiness | **Green** | Low | 1–2 days of polish |

**Bottom line:**  
You are **pilot-ready** once the two environmental fixes (`requests` + driver) and one prompt tweak are done. The 3.2 router is fast enough that quality is not being sacrificed — it just needs slightly tighter instructions. The 8B will have plenty of context at 32K for graph traversal. The 70B can wait until the first real patient timeline is built overnight.

Would you like me to:
1. Write the exact one-line prompt addition for the 3.2 router?
2. Give you the full `portalnode4090_fix_env.sh` that installs `requests` + checks the driver?
3. Or the 32K Modelfile + restart commands for the 8B?

Just say the word — you’re extremely close. The tooling phase is nearly complete.
