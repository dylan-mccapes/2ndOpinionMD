# PortalNode-01 — VC Presentation Package

**Date:** 2026-04-11
**System:** PortalNode-01 — On-premise HIPAA-ready inference server
**BOM Estimate:** ~$10,500
**Purpose:** Investor-ready documentation and visual assets for the tiered eoh-llama deployment powering 2ndOpinionMD + RISE Computable Flare Detection

---

## Package Contents

### `/technical/`

| File | Description |
|------|-------------|
| `portalnode_01_spec.json` | SpecDriver component-graph spec — 12 parts, 14 edges, 14 image stages, full BOM |
| `VC_DECK_RISE_ONPREM_20260411.md` | Investor presentation narrative — market timing, unit economics, scalability path |

### `/conceptual/` — Interactive Diagrams (open in browser, screenshot at any resolution)

| File | Description |
|------|-------------|
| `01_model_tiering_gpu_allocation.html` | **Model tiering** — 3.2 + 8B share GPU 0, 70B tensor-parallel on GPUs 1+2, GPU 3 hot spare. Includes VRAM usage, latency, throughput, and traffic distribution. |
| `02_datavant_ehr_pipeline_70b.html` | **EHR data pipeline** — Datavant → EHR ingest (heuristic pre-extract) → 70B deep synthesis (4-8 hrs) → Knowledge Graph. Timeline bar with per-stage estimates. |
| `03_ogre_8b_graph_enrichment.html` | **OGrE enrichment** — 5-step walkthrough of how 8B traverses the graph in idle cycles: node selection, neighborhood scan, edge proposal, mutation + receipt, and 70B escalation gate. Animated SVG graph visualization. |
| `portalnode_01_deployed.png` | Full system deployed and cabled in hospital data center rack |

### `/hardware/` — SpecDriver-generated Hardware Images (DALL-E)

| File | Description |
|------|-------------|
| `00_chassis_overview.png` | Rosewill RSV-L4500U 4U chassis exterior |
| `00_the_appliance.png` | PortalNode-01 appliance overview |
| `01_gpu_array.png` | 4× RTX 4090 Founders Edition array |
| `01_the_interior.png` | Internal component layout |
| `02_cpu_memory.png` | Xeon w5-2465X + 128 GB ECC DDR5 |
| `02_three_tools.png` | Model tiering metaphor (v1) |
| `03_data_flow_pipeline.png` | Data flow diagram (v1) |
| `03_storage_array.png` | Samsung 990 Pro + Sabrent Rocket NVMe |
| `04_air_gap.png` | HIPAA air-gap architecture |
| `04_power_thermal.png` | Corsair AX1600i PSU + Noctua cooling |
| `05_network_topology.png` | Dual 10 GbE + IPMI topology |
| `05_scale_comparison.png` | Scale comparison |
| `06_rack_deployed.png` | Rack-deployed system |
| `06_software_stack.png` | Ubuntu + Docker + Ollama stack |
| `07_model_tiering.png` | Model tiering diagram (v1) |
| `08_rise_data_flow.png` | RISE data flow (v1) |
| `09_full_system_assembled.png` | Full assembled system |

---

## How to Use the Conceptual Diagrams

The three HTML files in `/conceptual/` are self-contained, single-file web pages. To produce presentation-ready images:

1. Open any `.html` file in Chrome or Safari
2. The diagram renders at 1200px width on a dark background
3. Screenshot or use Chrome DevTools → Capture Node Screenshot for pixel-perfect export
4. All text, stats, and labels render natively — zero hallucination risk

These replace DALL-E-generated conceptual images which had text hallucination issues.

---

## Architecture Summary

```
┌─────────────────────────────────────────────────────┐
│                   PortalNode-01                     │
│           4U Rack · ~$10.5K · 2.2 kW               │
│                                                     │
│  GPU 0 (always-on)     GPU 1+2 (on-demand)   GPU 3 │
│  ┌──────────────┐     ┌──────────────────┐   ┌───┐ │
│  │ eoh-llama 3.2│     │  eoh-llama 70B   │   │HOT│ │
│  │   2 GB VRAM  │     │   40 GB VRAM     │   │SPR│ │
│  │  <300ms  10% │     │   tensor-parallel│   │   │ │
│  ├──────────────┤     │   <4s        8%  │   │   │ │
│  │ eoh-llama 8B │     └──────────────────┘   └───┘ │
│  │   5 GB VRAM  │                                   │
│  │  <1.2s   82% │     FastAPI router on CPU         │
│  └──────────────┘     ProvenanceEngine receipts     │
│                                                     │
│  Datavant EHR ──→ Ingest ──→ 70B Graph Build        │
│                        └──→ 8B OGrE (24/7)          │
│                                                     │
│  🔒 HIPAA air-gapped · zero cloud dependency        │
└─────────────────────────────────────────────────────┘
```

---

*Package assembled 2026-04-11 · PortalVision / 2ndOpinionMD*
