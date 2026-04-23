# Game plans & strategies

Product and engineering roadmaps, UX plans, and traversal strategy docs for 2ndOpinionMD-MVP.

| Artifact | Purpose |
|----------|---------|
| `../reports/STRATEGY_GRAPH_TRAVERSAL.md` | **Core 12** PTV graph tools for agents (executable via `server/graph_traversal/agent_tools.py`) |
| `GAME_PLAN_GRAPH_TRAVERSAL.md` | Full research catalog (80+ strategies) |
| `GAME_PLAN_COMFORT_UX.md` | COMFORT_UX rollout blocks |
| `GAME_PLAN_STRIPE_GATING.md` | Subscription gating (Journal free; Timeline + Detective paid) |
| `GAME_PLAN_MOCK_SERVER.md` | Frontend mock API server |
| `GAME_PLAN_*PORTAL*.md` | Patient/doctor portal and ambient coding |
| `GAME_PLAN_TIMELINE_*.md` | Timeline charts and upload/EoHD |
| `../reports/STRATEGY_*.md` | Historical strategy memos (graph, B2B, EoHD) — consolidated under `reports/` |

Code entry point for graph tools: `execute_graph_tool(name, vision, args)` in `server/graph_traversal/agent_tools.py`.

**Sandbox:** `sandbox/norman_graph_retrieval/` — run graph retrieval + optional Ollama `eoh-llama-lucifer` against the Norman PTV JSON (see that folder’s README).
