(.BeatingHeart) debian-dylan@magnifying-ocean:/mnt/c/2OPMD/2ndOpinionMD-MVP$ python sandbox/norman_graph_retrieval/tool_agent_harness.py   -q "CRP and joint symptoms"   --max-json-chars 24000   --max-context-nodes 48   --context-preview-chars 480   --final-synthesis-max-candidates 80   --final-synthesis-preview-chars 350
[tool-harness] ✅ Ollama OK; model 'eoh-llama-lucifer' available as 'eoh-llama-lucifer:latest'
[tool-harness] ==============================================================================
[tool-harness] 📋 SESSION  (copy/paste this block for bug reports or demos)
[tool-harness] ==============================================================================
[tool-harness] 📂 PTV file: /mnt/c/2OPMD/2ndOpinionMD-MVP/artifacts/timeline_ollama_20260329_1805/patient_timeline_vision_norman_eric_roberts_20260329_195915.json
[tool-harness] 👤 patient_id=norman_eric_roberts
[tool-harness] 📊 timeline events loaded: 7705
[tool-harness] 💬 clinical query: 'CRP and joint symptoms'
[tool-harness] 🔎 semantic hybrid: ON  (keyword-only if OFF)
[tool-harness] 🤖 eoh-llama per round: ON
[tool-harness] 🌐 OLLAMA_URL='http://127.0.0.1:11434'  OLLAMA_MODEL='eoh-llama-lucifer'
[tool-harness] 🧬 pe_nodes (PE + working set cap): 400
[tool-harness] 📏 max_json_chars (prompt to LLM): 24000
[tool-harness] 🧩 max_context_nodes (PTV previews per round): 48
[tool-harness] 📎 context_preview_chars (per node): 480
[tool-harness] 📬 final synthesis JSON: ON (candidates≤80, preview≤350)
[tool-harness] 📅 temporal reduce: ON  recent_years=1.0  anchor='latest_in_corpus'
[tool-harness] 📦 full_tool_json in output file: NO (result_summary only)
[tool-harness] ➕ extra-rounds: (none)
[tool-harness] ------------------------------------------------------------------------------
[tool-harness]
[tool-harness] 🚀 Tool Agent Harness — flagship STRATEGY v1.1 + native PE cross-check
[tool-harness]    Flow: structural reduce → temporal reduce → hybrid (semantic) → BFS → Lorenz → govern → token budget → PE → [extras]
[tool-harness]    Temporal window: recent_years=1.0  anchor='latest_in_corpus'
[tool-harness]
[tool-harness] ------------------------------------------------------------------------------
[tool-harness] ROUND 1/8  ✂️  step='reduce'  tool=graph_reduce
[tool-harness]    📌 Structural graph_reduce: pages, isolates, etc. → baseline corpus
[tool-harness]    ⚙️  deterministic tool finished in 4.8 ms
[tool-harness]    📊 strategy=S2 kept=3705 dropped=4000 event_ids_returned~3705
[tool-harness]       🤖 LLM OK — 1414 chars
[tool-harness]          💬 This step used the graph_reduce tool with strategy_id S2 to reduce the Patient Timeline Vision (PTV). The tool output includes a list of dropped samples, which are events that were removed from the PTV due to being isolated or having no connections. The context_nodes section provides information about 48 nodes in the reduced PTV. These nodes include lab r...
[tool-harness]    ⏱️  LLM call took 64963.7 ms  (model='eoh-llama-lucifer')
[tool-harness] ------------------------------------------------------------------------------
[tool-harness] ROUND 2/8  📅  step='temporal_reduce'  tool=graph_reduce
[tool-harness]    📌 Temporal slice on same rules + time window → flagship corpus for hybrid/BFS
[tool-harness]    ⚙️  deterministic tool finished in 49.3 ms
[tool-harness]    📊 strategy=S2 kept=146 dropped=7559 event_ids_returned~146 temporal=[2024-12-05T00:00:00+00:00..2025-12-05T00:00:00+00:00]
[tool-harness]       🤖 LLM OK — 1338 chars
[tool-harness]          💬 This step, `temporal_reduce` using tool `graph_reduce`, has processed a large number of events in the Patient Timeline Vision (PTV). The key findings are: * 7559 events were dropped due to reasons such as "page", "isolate", and "temporal_unparsed_date". * 146 events were kept, with their corresponding preview text available. * The temporal filter used a t...
[tool-harness]    ⏱️  LLM call took 61363.2 ms  (model='eoh-llama-lucifer')
[tool-harness] ------------------------------------------------------------------------------
[tool-harness] ROUND 3/8  🔎  step='hybrid_search'  tool=graph_hybrid_search
[tool-harness]    📌 Hybrid search (semantic + keyword) on temporal/reduced event_ids only
Warning: You are sending unauthenticated requests to the HF Hub. Please set a HF_TOKEN to enable higher rate limits and faster downloads.
Loading weights: 100%|██████████████████████████████████████████████████████████████| 103/103 [00:00<00:00, 2644.77it/s]
BertModel LOAD REPORT from: sentence-transformers/all-MiniLM-L6-v2
Key                     | Status     |  |
------------------------+------------+--+-
embeddings.position_ids | UNEXPECTED |  |

Notes:
- UNEXPECTED    :can be ignored when loading from different task/architecture; not ok if you expect identical arch.
[tool-harness]    ⚙️  deterministic tool finished in 7537.1 ms
[tool-harness]    📊 strategy=S11 merged_hits=30 kw=5 sem=30 scope=subset corpus_n=146
[tool-harness]       🤖 LLM OK — 1702 chars
[tool-harness]          💬 This step used the graph_hybrid_search tool to search for connections between CRP and joint symptoms in the Patient Timeline Vision (PTV). The tool returned a list of 30 event IDs with associated preview text, edge counts, and connascence counts. The tool output indicates that there are several events related to joint symptoms, including: * pdf_p4200_e000...
[tool-harness]    ⏱️  LLM call took 62600.3 ms  (model='eoh-llama-lucifer')
[tool-harness] ------------------------------------------------------------------------------
[tool-harness] ROUND 4/8  🕸️  step='bfs_expand'  tool=graph_bfs_expand
[tool-harness]    📌 Multi-seed BFS inside reduced set → neighborhood for PE / working set
[tool-harness]    ⚙️  deterministic tool finished in 0.3 ms
[tool-harness]    📊 strategy=S4 expanded_event_ids=87
[tool-harness]       🤖 LLM OK — 1292 chars
[tool-harness]          💬 This step, `bfs_expand`, used the graph_bfs_expand tool to expand the Patient Timeline Vision (PTV) with a maximum depth of 2. The tool output includes a list of all expanded nodes (`event_ids`) and their corresponding context information. The operator can see that the PTV has been expanded to include 48 nodes, each with its own preview text, timestamp, a...
[tool-harness]    ⏱️  LLM call took 53462.5 ms  (model='eoh-llama-lucifer')
[tool-harness] ------------------------------------------------------------------------------
[tool-harness] ROUND 5/8  🌀  step='pe_lorenz'  tool=graph_pe_lorenz_classify
[tool-harness]    📌 In-repo Lorenz classify on working_ids (ρ/τ attractor)
[tool-harness]    ⚙️  deterministic tool finished in 1079.6 ms
[tool-harness]    📊 strategy=S8 items=99 labels=[EVICT=8, KEEP=35, REVIEW=56]
[tool-harness]       🤖 LLM OK — 1439 chars
[tool-harness]          💬 This step ran a graph tool called `graph_pe_lorenz_classify` to analyze the patient's timeline. The output includes various event IDs with their corresponding classifications, mean x values, load-bearing status, and other metadata. The context nodes section provides more detailed information about each event, including the preview text, which is a clinica...
[tool-harness]    ⏱️  LLM call took 84233.7 ms  (model='eoh-llama-lucifer')
[tool-harness] ------------------------------------------------------------------------------
[tool-harness] ROUND 6/8  ⚖️  step='pe_govern'  tool=graph_pe_govern_adjust
[tool-harness]    📌 Governance: protect load-bearing from silent EVICT
[tool-harness]    ⚙️  deterministic tool finished in 0.2 ms
[tool-harness]    📊 strategy=S10 governance_rows=99
[tool-harness]       🤖 LLM OK — 1608 chars
[tool-harness]          💬 This step used the graph_pe_govern_adjust tool to analyze the Patient Timeline Vision (PTV). The tool output includes classifications of events as either KEEP, REVIEW, or EVICT, with some events having a reason provided. The context_nodes section provides more detailed information about each event, including its type, timestamp, preview text, and connasce...
[tool-harness]    ⏱️  LLM call took 70981.5 ms  (model='eoh-llama-lucifer')
[tool-harness] ------------------------------------------------------------------------------
[tool-harness] ROUND 7/8  🪙  step='token_budget'  tool=graph_token_budget
[tool-harness]    📌 Token budget: rank events for downstream LLM context
[tool-harness]    ⚙️  deterministic tool finished in 0.6 ms
[tool-harness]    📊 strategy=S3 picked_events=30 est_tokens~673/8000 considered=30
[tool-harness]       🤖 LLM OK — 1242 chars
[tool-harness]          💬 This step, token_budget, ran the graph_token_budget tool against a Patient Timeline Vision (PTV). The tool output includes 30 context nodes with preview text, which provide relevant information about each event. The key findings from this step are: * The patient has been prescribed various medications for constipation and fever, including Acetaminophen (T...
[tool-harness]    ⏱️  LLM call took 43264.6 ms  (model='eoh-llama-lucifer')
[tool-harness] ------------------------------------------------------------------------------
[tool-harness] ROUND 8/8  🧪  step=provenance_engine  tool=provenance_engine.classify
[tool-harness]    📌 Native provenance-engine classify (cross-check vs Lorenz)
[tool-harness]    🧬 vision_to_pe_nodes: 99 nodes (cap pe_nodes=400)
[tool-harness]    ⚙️  native provenance_engine.classify finished in 220.2 ms
[tool-harness]    📊 native_PE ok=True items=99 node_count=99 labels=[EVICT=10, KEEP=57, REVIEW=32]
[tool-harness]       🤖 LLM OK — 1323 chars
[tool-harness]          💬 Based on the provided JSON output, I'll summarize the key findings related to CRP and joint symptoms. **CRP:** * There is one event related to a lab result with a preview of "CR0.97" (event_id: pdf_p4204_e0000). This suggests that the patient's CRP level was 0.97, which may indicate an inflammatory response. * However, there are no other events directly m...
[tool-harness]    ⏱️  LLM call took 78664.5 ms  (model='eoh-llama-lucifer')
[tool-harness] ------------------------------------------------------------------------------
[tool-harness] FINAL SYNTHESIS  (structured JSON: response + suggested_nodes + full PTV)
[tool-harness]    candidates considered: 80  |  LLM ms: 41452.8
[tool-harness]    suggested_nodes (normalized): 2
[tool-harness] ------------------------------------------------------------------------------
[tool-harness] ------------------------------------------------------------------------------
[tool-harness] ✅ Harness run finished in 570.05 s  |  total rounds written: 8
[tool-harness]    (7 graph tools + 1 native PE — each round may include an eoh-llama analysis block in the JSON)
[tool-harness] ==============================================================================
[tool-harness] 📄 JSON written: /mnt/c/2OPMD/2ndOpinionMD-MVP/sandbox/norman_graph_retrieval/out/tool_agent_harness_20260413_200940.json
[tool-harness] 📝 Inspection log (full tool JSON + LLM text): /mnt/c/2OPMD/2ndOpinionMD-MVP/sandbox/norman_graph_retrieval/out/tool_agent_harness_20260413_200940.log
[tool-harness] 📊 rounds in file: 8  |  wall_time_s: 570.054
[tool-harness]    final_synthesis: OK (response + suggested_nodes in JSON)
[tool-harness]    .log: tool rounds + final block (success or failure receipt).
[tool-harness] ==============================================================================

--------------------------------------------------------------------------------
EXECUTIVE SUMMARY
--------------------------------------------------------------------------------

Outcome: Full successful run. Ollama preflight passed; all eight rounds (seven graph tools
plus native provenance_engine) and final synthesis completed with no reported failures.
Wall time was about 9.5 minutes, driven almost entirely by per-round eoh-llama latency
(roughly 43–84 s per LLM call), not by deterministic graph tools (milliseconds to ~7.5 s
for first hybrid load).

Pipeline: The flagship path behaved as intended—structural reduce (7,705 to 3,705 events),
temporal reduce to a one-year window anchored on latest corpus date (146 events in
[2024-12-05, 2025-12-05]), semantic hybrid on that subset (30 merged hits), BFS expansion
(87 events), Lorenz classify and govern (99 rows), token budget (30 events ranked), then
native PE on 99 nodes for cross-check. Lorenz versus native PE label histograms differed
(EVICT/KEEP/REVIEW counts), which is expected for a sanity cross-check rather than identity.

Embeddings: First hybrid round triggered sentence-transformers load from Hugging Face
(unauthenticated hub warning once), MiniLM weights loaded; benign BertModel position_ids note.

Deliverables: JSON and inspection log written under sandbox/norman_graph_retrieval/out/
(tool_agent_harness_20260413_200940.{json,log}). Final synthesis normalized two suggested
nodes from an 80-candidate pool.

Follow-ups (optional): Set HF_TOKEN if doing many runs against the Hub; if end-to-end latency
must drop, profile Ollama inference or reduce rounds/context rather than graph code—the
deterministic stage is already cheap.
