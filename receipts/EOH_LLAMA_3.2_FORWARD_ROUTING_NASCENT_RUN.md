(.venv_embed) hilarious_marcupial@DESKTOP-KOMPK5V:/mnt/c/Users/dylan/2ndOpinionMD-MVP$ bash scripts/portalnode
4090_source_router_harness.sh \
 T2DM>   "First-line therapy for T2DM with CKD considerations" \
>   --max-sources 8 \
>   --max-modules 6 \
>   --out receipts/FORWARD_SOURCE_ROUTER_NASCENT_RUN_20260425.json
🚀 Starting EoH source-router harness
❓ Query ready (51 chars)
📚 Loaded source candidates: 38
🧩 Loaded module candidates: 41
🤖 Ollama call model=eoh-llama3.2-source-router num_ctx=8192 timeout=120s
✅ Router model completed in 5.340s
{
  "query": "First-line therapy for T2DM with CKD considerations",
  "model": "eoh-llama3.2-source-router",
  "max_sources": 8,
  "max_modules": 6,
  "source_candidates_count": 38,
  "module_candidates_count": 41,
  "route_plan": {
    "question_type": "E",
    "semantic_query": "First-line therapy for T2DM with CKD considerations",
    "ts_query": "t2dm AND ckd",
    "ts_terms": [
      "T2DM",
      "CKD"
    ],
    "selected_sources": [
      {
        "source": "kdigo_ckd_2021",
        "priority": 1,
        "why": "covers T2DM and CKD"
      }
    ],
    "selected_modules": [
      {
        "module_id": "M13",
        "priority": 1,
        "why": "provides trend & prognostic engine for flare risk over next X days/months"
      }
    ],
    "notes": "Use KDIGO 2021 CKD guideline and T2DM treatment recommendations"
  }
}
💾 Wrote output file: receipts/FORWARD_SOURCE_ROUTER_NASCENT_RUN_20260425.json
🏁 Source-router harness complete

---

## Meta-commentary (assistant)

- The router returned a structurally valid plan and respected bounds (`max_sources=8`, `max_modules=6`) but was under-selective (1 source, 1 module).
- `question_type="E"` looks weak for this prompt; T2DM+CKD first-line therapy is usually treatment/planning-oriented (`D`) with some trajectory (`A/C`).
- Query expansion quality is minimal (`semantic_query` unchanged; `ts_query` = `t2dm AND ckd`), so recall for mixed guideline/ontology corpora will likely be limited.
- Module choice `M13` (trend/prognostic) is reasonable but incomplete; routing should often include planning/governance modules when therapy prioritization is asked.
- Next step: run the new 10-query router batch harness and measure diversity/coverage (question_type distribution, avg selected sources/modules, and lexical expansion depth).