# REPORT: BloomForge Simulation Status & Living Body Graph Proposal

**Date:** 2026-03-30  
**Author:** Dylan (PortalVision)  
**Contributors:** Andras Hangyal (organ-as-compute seed idea), Aetherios (Modelfile analysis)  
**Hardware:** Bloom (HP Victus, RTX 4050, 6 GB VRAM) · Dylan (RTX 4090, 24 GB VRAM) · M2 Ultra Mac Studio  
**Module candidate:** M69 (Living Body Graph Simulation Engine)  
**Status:** Proposal stage — ready for design specification

---

## 1. BloomForge Simulation Program — Current State

BloomForge has delivered **12 complete simulation suites** across 9 scientific domains in 19 days (2026-03-11 to 2026-03-30). All suites ran on Bloom (RTX 4050, `.PlumeWalker` venv, CuPy + numpy + matplotlib). No external compute was required.

### Delivered Suites

| Suite | Date | Domain | Predicates | Key Finding |
|-------|------|--------|------------|-------------|
| **S4 GPU Structured Noise** | 03-11 | Exciton / quantum noise | S4b/S4c met; S4a/S4d bio-zone not met | Baseline rank 60.7% at σ ≈ 78–96 cm⁻¹ |
| **Overnight P1/P2/3D** | 03-12 | Field genesis, agent swarm, 3D routing | Clean GPU completion | P1 spectral slope invariant (−3.069); P2 48.4% delivery; 3D 96.3% |
| **FGSI Glycocalyx G1–G6** | 03-13 | Glycocalyx degradation, autoimmune detection | Narrative validation | MiraLAX chronic FGSI ~0.17; detection window ~3.7 days (severe) |
| **M68 ICM C1–C7** | 03-13 | Inflammatory capacity ODE | R² = 0.978 vs FGSI G2 | Daily limit cycle aligns with G5d; overflow threshold δ ≈ 0.15 |
| **Convective Hail W1–W5** | 03-17 | Mesoscale hail + ENAQT overlay | 5/5 validated | W4 real geometry 77.8th percentile vs 10k variants |
| **Cryo Routing CR1–CR6** | 03-16 | Cold/damaged routing, lock-in | CR6 monotonic FGSI gradient | CR3 ~14.5% lock-in; CR2 53% queue drop at 600 ts |
| **Friction NSFT F1–F5** | 03-20 | Molecular friction, stick-slip | **15/19** (79%) | F4/F5 flagged predicates — parameterization issues |
| **Variance · Hydrogen** | 03-20 | 5D embedding, perturbations, stealth vision | **17/20** (85%) | Baseline fragility 44.5%; V3 clean stall angle; V5 cross-modal convergence |
| **Agent-Field H₂ v1** | 03-11 | OpenMM H1–H6 | **5/8** (63%) | H6 fragility 44.5% → 54.9%; 0 physics failures |
| **Agent-Field V2 Full** | 03-21 | OpenMM H1–H13, explicit diatomics | **31/32** (96.9%) | H6 fragility 61.2%; H13 N₂→H₂ collision dynamics operational |
| **Breathe V4/V5 BR1–BR14** | 03-11 | Respiratory backwards embedding | 11 pass / 2 partial / 0 bug | Krogh, CO₂ stall ENAQT, cell plume verified |
| **March Madness Monte Carlo** | 03-27 | Sports bracket, NSFT stealth profiles | N/A (fun) | 50k sims; Michigan 30.2%, Florida 28.7% |

**Aggregate program health:** 12 suites, ~130 total predicates evaluated across all deliveries. Agent-Field V2 reached 96.9% pass rate — the program's high-water mark. Failures are consistently parameterization or test design, not physics.

### Infrastructure Maturity

The forge now has proven GPU-accelerated building blocks for:

| Capability | Code | Used By |
|-----------|------|---------|
| 2D reaction-diffusion PDE (5-point stencil) | `field_genesis_gpu.py` | G1, G2, G5, CR suites |
| 2D agent swarm (gradient + Brownian) | `agent_swarm_gpu.py` | G3, P2, agent-field |
| Batched Lindblad/RK4 (CuPy) | `s4_gpu_kernels.py` | G4, S4 suites |
| FFT-based Laplacian (3D, CuPy) | `routing_3d_gpu.py` | Overnight 3D, cryo routing |
| OpenMM molecular dynamics (CUDA) | `openmm_setup.py` | Agent-Field H1–H13 |
| 5D force-directed graph embedding | `variance_embedding.py` | Variance · Hydrogen |
| Respiratory ODE backwards embedding | Breathe suite | BR1–BR14 |

---

## 2. The Living Body Graph — Dylan's Architecture

### Origin

Andras proposed the seed idea in Signal (2026-03-30): *"Each Organ is its own Compute and processing engine."* He flagged it as a candidate for Module 69.

Dylan expanded this into a full architecture:

> "BloomForge (or I) can simulate anything. Simulations are what I am best at. It's inevitable now. I am imagining a state graph. That state graph is a human. The nodes are what matters (not necessarily organs, processes too). We create the graph first then we isolate each node. Then we simulate each node standalone. Then we create a GameEngine that monitors all of the nodes for input. Then we simulate everything based on input to the graph (sensory, food, drugs, sadness, etc). We will need two graphs: the body graph and the input graph. The input graph responds to perturbation which cascades into the body graph. The body graph handles nodes as processes on dedicated cores. Both graphs are alive."

### What This Means

This is not an organ simulator. This is a **living state graph of a human being**. The key departures from a naive organ-per-GPU model:

1. **Nodes are not necessarily organs.** They are *whatever matters* — an organ, a biochemical process, a regulatory loop, a psychological state, a microbiome community. "Glycocalyx maintenance" is a node. "Sleep architecture" is a node. "Grief" is a node. The graph's ontology emerges from what you need to simulate, not from an anatomy textbook.

2. **Two graphs, not one.** The **body graph** represents internal state and processes. The **input graph** represents the external world impinging on the body — sensory input, food, drugs, emotional events, environmental stressors, time of day. Perturbation enters the input graph first and cascades into the body graph through defined edges. This separation is critical: it means you can replay the same body graph under different input scenarios, or apply the same input stream to different body configurations.

3. **The GameEngine.** A real-time orchestrator that monitors all nodes for input, routes perturbation cascades, manages timescale synchronization between fast nodes (neural, cardiac) and slow nodes (immune, tissue remodeling), and decides when a node needs to wake up and recompute. This is not batch simulation — both graphs are **alive**, continuously running, event-driven.

4. **Dedicated cores per node.** The body graph distributes node computation across hardware. Each node is a process on a dedicated core (or GPU thread block). The GameEngine is the scheduler. This maps directly onto BloomForge's existing infrastructure: each simulation suite is already an independent compute unit. The GameEngine formalizes the orchestration that is currently done manually via inbox/outbox.

### Architecture Diagram

```
                    ┌─────────────────────────────┐
                    │        INPUT GRAPH           │
                    │                              │
                    │  food ─── drugs ─── sensory  │
                    │    │        │         │      │
                    │  sadness ─ sleep ─── toxins  │
                    │    │        │         │      │
                    │  exercise  time    microbiome│
                    └────────────┬─────────────────┘
                                 │ perturbation cascade
                                 ▼
                    ┌─────────────────────────────┐
                    │        GAME ENGINE           │
                    │  (monitor · route · sync)    │
                    └────────────┬─────────────────┘
                                 │ dispatches to nodes
                                 ▼
   ┌─────────────────────────────────────────────────────────────┐
   │                      BODY GRAPH                             │
   │                                                             │
   │  ┌──────────┐   ┌──────────┐   ┌──────────┐               │
   │  │ gut      │──▶│ liver    │──▶│ kidney   │               │
   │  │ epithel. │   │ first-   │   │ clearance│               │
   │  │ [G1-G6]  │   │ pass     │   │          │               │
   │  └────┬─────┘   └────┬─────┘   └──────────┘               │
   │       │              │                                      │
   │       ▼              ▼                                      │
   │  ┌──────────┐   ┌──────────┐   ┌──────────┐               │
   │  │ glycoca- │   │ ICM      │◀──│ lung     │               │
   │  │ lyx mnt  │──▶│ inflam.  │   │ O₂/CO₂  │               │
   │  │ [FGSI]   │   │ capacity │   │ [BR1-14] │               │
   │  └──────────┘   │ [C1-C7]  │   └──────────┘               │
   │                  └────┬─────┘                               │
   │                       │                                     │
   │                       ▼                                     │
   │  ┌──────────┐   ┌──────────┐   ┌──────────┐               │
   │  │ immune   │   │ nervous  │   │ cardio-  │               │
   │  │ lymph    │◀──│ system   │──▶│ vascular │               │
   │  │ [Variance│   │ vagal    │   │ [CR1-6]  │               │
   │  │  graph]  │   │ tone     │   │          │               │
   │  └──────────┘   └──────────┘   └──────────┘               │
   │                                                             │
   │  Each node: state + step(dt) + snapshot()                   │
   │  Each node: process on dedicated core                       │
   │  Edges: typed, directional, with transform functions        │
   └─────────────────────────────────────────────────────────────┘
```

### Mapping Existing BloomForge Work to Graph Nodes

The forge has already built node-ready simulations:

| BloomForge Suite | Body Graph Node | What It Already Simulates |
|-----------------|-----------------|--------------------------|
| **FGSI G1–G6** | `gut_epithelium`, `glycocalyx_maintenance` | Glycocalyx field, osmotic stripping, structural damage, recovery, chronic dosing |
| **M68 ICM C1–C7** | `inflammatory_capacity` | Allostatic load, 3-valve dynamics, overflow cascade, turbulence regime |
| **Breathe BR1–BR14** | `lung_exchange`, `bronchial_routing` | O₂/CO₂ exchange, Krogh diffusion, alveolar field |
| **Agent-Field H1–H13** | `molecular_transport` | Particle dynamics, embedding feedback, collision boundaries |
| **Cryo Routing CR1–CR6** | `circulatory_routing` | Cold damage, queue congestion, lock-in, protocol-driven recovery |
| **Variance · Hydrogen** | `immune_graph_structure` | 5D embedding, tolerance cascade, fragility dynamics |
| **Friction NSFT F1–F5** | `boundary_mechanics` | Stall, stick-slip, friction at tissue interfaces |

### Why Two Graphs Is the Right Call

1. **Separation of concerns.** The body graph models *what you are*. The input graph models *what happens to you*. Changing your diet is an input graph mutation, not a body graph mutation. Getting diagnosed with Crohn's changes the body graph. This distinction is exactly what EoH already makes: CBM (chronic baseline mode) is body graph state; environmental stressors are input graph perturbations.

2. **Replay and counterfactual.** With two graphs you can ask: "What if this patient had the same body graph but never took MiraLAX daily?" Swap the input graph, re-run. This is the simulation equivalent of the Detective's differential diagnosis — but grounded in mechanistic dynamics rather than LLM inference.

3. **Matches ICM's three valves.** Inflow valve = input graph → body graph edge weights. Displacement volume = body graph node chronic state. Outflow valve = body graph clearance node capacity. The GameEngine manages the cascade.

4. **Matches FUDD (M64).** The input graph delivers nutrients. The body graph's absorption nodes determine what actually gets utilized. The delta between input delivery and node absorption is functional utilization discordance — computed mechanistically.

### Where the Hard Problems Are

1. **Graph ontology.** What are the nodes? This is the first design decision and the most consequential. Too fine-grained (every enzyme is a node) and the graph is uncomputable. Too coarse (5 organs) and it can't answer real clinical questions. The sweet spot is probably 30–80 nodes spanning organs, major biochemical pathways, regulatory loops, and psychological state variables. The graph itself should be designed by Andras (clinical ontology) and validated by simulation (does each node produce meaningful standalone dynamics?).

2. **Timescale synchronization.** Neural signals propagate in milliseconds. Cardiac cycles are seconds. Gut transit is hours. Immune responses are days. Tissue remodeling is weeks. The GameEngine must handle nodes running at wildly different rates without drift or deadlock. Adaptive time-stepping per node, with the GameEngine enforcing synchronization barriers at communication points.

3. **The GameEngine is the hardest piece.** It's a real-time scheduler, event router, timescale synchronizer, and cascade propagator. It needs to be fast enough that the simulation feels alive, not batch. This is game engine territory — hence the name. Consider existing frameworks (ECS architectures, discrete event simulation libraries) before building from scratch.

4. **"Both graphs are alive."** This means persistent state, continuous evolution, no batch boundaries. The simulation doesn't start and stop — it runs. Input events arrive asynchronously. The body graph responds. This is architecturally different from everything BloomForge has built so far (all batch, all offline). The transition from batch to live is a real engineering challenge.

---

## 3. M69 Sketch: Living Body Graph Simulation Engine

### The Two Graphs

```
InputGraph:
  nodes: Dict[str, InputNode]        # sensory, food, drugs, emotional, environmental, temporal
  edges: List[InputEdge]             # perturbation propagation within input domain
  
  perturb(node_id, event) -> None    # inject external event
  cascade() -> Dict[str, Signal]     # propagate and emit signals toward body graph

BodyGraph:
  nodes: Dict[str, BodyNode]         # organs, processes, regulatory loops, states
  edges: List[BodyEdge]              # typed, directional, with transform functions
  
  receive(signals: Dict) -> None     # accept cascaded input from InputGraph
  step(dt) -> None                   # advance all nodes (dispatched to cores)
  snapshot() -> Dict                 # serialize full graph state
  
  alive: bool = True                 # continuously running
```

### Node Interface Contract

```
BodyNode:
  name: str                          # e.g. "gut_epithelium", "sleep_architecture", "grief"
  node_type: str                     # "organ" | "process" | "regulatory" | "psychological"
  
  inputs: Dict[str, Channel]         # named input channels (from edges + InputGraph)
  state: Dict[str, float | array]    # internal state variables
  outputs: Dict[str, Channel]        # named output channels (to edges)
  
  dt_native: float                   # node's natural timestep (ms for neural, hours for immune)
  step(dt) -> None                   # advance one timestep
  snapshot() -> Dict                 # serialize state
  
  predicates: List[Predicate]        # standalone validation criteria
  validate() -> PredicateReport      # run predicates against current state
```

### The GameEngine

```
GameEngine:
  body: BodyGraph
  input: InputGraph
  
  monitor() -> None                  # watch all nodes for input arrival
  route(signal, source, target) -> None   # dispatch perturbation along edges
  sync() -> None                     # synchronization barrier for multi-rate nodes
  
  run() -> None                      # main loop — both graphs alive, event-driven
  replay(input_log) -> Timeline      # counterfactual: same body, different inputs
```

### Build Sequence

| Phase | What | BloomForge Base | Deliverable |
|-------|------|-----------------|-------------|
| **0: Graph design** | Define node ontology (30–80 nodes). Andras designs clinical graph; Dylan validates computability. | All existing suites inform node selection | `BODY_GRAPH_V0.jsonl` + `INPUT_GRAPH_V0.jsonl` |
| **1: Isolate** | Wrap 5 existing suites as standalone BodyNodes with standard interface | FGSI, ICM, Breathe, Variance, Cryo | 5 validated BodyNode implementations |
| **2: Pneuma v0** | Build the workflow isolation engine. Two nodes coupled: gut → ICM | New (Pneuma — workflow isolation, risk measurement, cascade, adapt) | Pneuma prototype, first isolated workflow |
| **3: InputGraph** | Define input node types and perturbation cascade logic | New (maps to EoH input taxonomy) | InputGraph with food/drug/stress/sleep nodes |
| **4: Scale** | Wire remaining nodes. Multi-rate sync. 10+ node body graph alive | Liver, kidney, nervous system = new builds | Living body graph running on 4090 |
| **5: Replay** | Counterfactual engine: same body, different input timelines | New | "What if no MiraLAX?" answerable by simulation |

---

## 4. Connection to 2OPMD / VC Narrative

Key framing points:

- **Edge deployment proven.** 12 simulation suites on a 6 GB laptop GPU. The living body graph runs on consumer hardware. Data sovereignty story writes itself for hospitals and VA systems.
- **The body graph feeds the Detective.** PTV extracts events from medical records (the patient's *actual* history). The body graph simulates what *should* happen given those events. The delta between simulation and observation is clinical signal — mechanistic, not just statistical. This is `answer_delta` grounded in physics.
- **Counterfactual medicine.** "What if this patient had never taken daily MiraLAX?" is answerable by replaying the body graph with a modified input graph. No other clinical decision support system can do this. Counterfactual replay is the feature that separates 2OPMD from pattern-matching EHR tools.
- **M69 bridges physics and clinical reasoning.** EoH modules M1–M68 operate on clinical abstractions (stack levels, stability bands, flare risk). M69 grounds those abstractions in mechanistic dynamics. When ICM says "inflow is high," M69 can say *which node* is contributing, *why*, and *what would happen if you changed the input*.
- **Hybrid compute architecture.** eoh-llama (8B, 8 GB) runs on the 4090 as the retrieval adapter. The body graph runs its nodes as GPU processes on the same hardware. Claude Opus handles narrative synthesis in the cloud. Local simulation + local adapter + cloud reasoning = the architecture VCs understand. The 70B model (42 GB, needs two 4090s) is a future option for bringing reasoning local too.

---

## 5. Recommendations

1. **Designate M69 — Living Body Graph.** The architecture has enough substance and existing implementation evidence to warrant a formal module number. The forge has already built 7 node-ready simulation suites. The two-graph + GameEngine architecture is Dylan's design; Andras seeded the organ-as-compute idea.

2. **Phase 0 first: design the graph.** Before writing any new simulation code, define the node ontology. What are the 30–80 nodes? Andras owns clinical ontology (which processes matter clinically). Dylan validates computability (can each node be simulated standalone with existing or near-term infrastructure). Output: `BODY_GRAPH_V0.jsonl` and `INPUT_GRAPH_V0.jsonl`.

3. **Wrap existing suites as BodyNodes.** FGSI, ICM, Breathe, Cryo Routing, and Variance already have code, predicates, and results. Formalizing them as BodyNodes with the standard interface is the fastest path to a working body graph prototype.

4. **Build the GameEngine on the 4090.** The GameEngine is the hardest and most novel piece. It's a real-time scheduler with multi-rate synchronization. The 4090 (24 GB) has headroom to run multiple node processes plus the GameEngine simultaneously. BloomForge (RTX 4050) continues standalone node development and validation.

5. **Ship "gut → ICM" as the first live cascade.** This is the minimum viable living body graph: two nodes, one edge, perturbation from the input graph (e.g., a MiraLAX dose) cascading through gut glycocalyx into systemic inflammatory capacity. If this works live, everything else is scaling.

6. **Andras reviews this report and the graph ontology proposal.** His "Module 69" suggestion and clinical expertise drive the node selection. The simulation map for the first coupled cascade should follow as a BloomForge outbox package.

---

*A state graph that is a human. Nodes are what matters. Both graphs are alive.*

**— Dylan (PortalVision), 2026-03-30**
