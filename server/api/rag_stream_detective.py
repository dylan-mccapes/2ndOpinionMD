# server/api/rag_stream_detective.py — EoH Detective (EoHD) stream mode
# Part of the 4-module split of rag_stream_custom_endpoints.py.
# Covers: eoh_detective_planner, detective_report_llm,
#          eoh_detective_stream_event_generator, eoh_detective_stream,
#          eoh_detective_stream_get.

from .rag_stream_shared import *  # noqa: F401,F403

async def eoh_detective_planner(
    *,
    client: Optional[OpenAI] = None,
    patient_id: str,
    focus: str,
    high_level_question: str,
    max_steps: int = 6,
    patient_snapshot: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    LLM-based planner for EoH Detective.

    Now timeline-aware via `patient_snapshot`, which may contain:
      - key_signals
      - diagnostic_landscape
      - diagnostic_landscape_history
      - span_days
      - timeline_summary (if available)

    Returns a JSON plan with:
    - patient_id
    - focus
    - steps: list of {step_id, kind, question_type, q, debug}
    """
    if client is None:
        client = OpenAI(timeout=60.0)

    # Payload sent to the planner LLM
    planner_input = {
        "patient_id": patient_id,
        "focus": focus,
        "high_level_question": high_level_question,
        "max_steps": max_steps,
        "patient_snapshot": patient_snapshot or {},
    }

    messages = [
        {
            "role": "system",
            "content": EOH_DETECTIVE_PLANNER_SYSTEM_PROMPT.strip(),
        },
        {
            "role": "user",
            "content": json.dumps(
                planner_input,
                ensure_ascii=False,
                cls=DateTimeJSONEncoder,
            ),
        },
    ]

    try:
        resp = await _chat_completion_async(
            model=CHAT_MODEL_UTIL,
            messages=messages,
            response_format={"type": "json_object"},
            temperature=0.0,
        )
        raw = resp.choices[0].message.content or "{}"
        plan = json.loads(raw)
    except Exception as e:
        logger.exception("eoh_detective_planner: LLM planning failed, using fallback plan")
        plan = {
            "patient_id": patient_id,
            "focus": focus,
            "steps": [
                {
                    "step_id": "A1",
                    "kind": "terrain_risk",
                    "question_type": "A",
                    "q": (
                        "Using this patient's entire timeline, summarize their major "
                        "clinical arcs and current Ethos-of-Health terrain. What were "
                        "the main inflection points (new diagnoses, major complications, "
                        "ICU transfers, surgeries, code events), and what are the 3–5 "
                        "dominant problems now? Ground your answer in the timeline, "
                        "including approximate dates and key labs/vitals/events. Do NOT "
                        "propose management yet; focus on mapping the terrain."
                    ),
                    "debug": False,
                }
            ],
            "planner_error": str(e),
        }

    # Normalize steps
    steps = plan.get("steps") or []
    normalized_steps: List[Dict[str, Any]] = []

    for i, step in enumerate(steps, start=1):
        sid = str(step.get("step_id") or f"S{i}")
        q = (step.get("q") or "").strip()
        if not q:
            continue
        normalized_steps.append(
            {
                "step_id": sid,
                "kind": str(step.get("kind") or "other"),
                "question_type": str(step.get("question_type") or "OTHER"),
                "q": q,
                "debug": bool(step.get("debug", False)),
            }
        )

    # Ensure A1 terrain step exists; if not, prepend one
    has_terrain = any(
        s.get("kind") == "terrain_risk" or s.get("step_id") == "A1"
        for s in normalized_steps
    )
    if not has_terrain:
        terrain_q = (
            "Using this patient's entire timeline, summarize their major "
            "clinical arcs and current Ethos-of-Health terrain. What were "
            "the main inflection points (new diagnoses, major complications, "
            "ICU transfers, surgeries, code events), and what are the 3–5 "
            "dominant problems now? Ground your answer in the timeline, "
            "including approximate dates and key labs/vitals/events. Do NOT "
            "propose management yet; focus on mapping the terrain."
        )
        normalized_steps.insert(
            0,
            {
                "step_id": "A1",
                "kind": "terrain_risk",
                "question_type": "A",
                "q": terrain_q,
                "debug": False,
            },
        )

    # Respect max_steps (planner is encouraged to use up to this, but we hard-cap here)
    if len(normalized_steps) > max_steps:
        normalized_steps = normalized_steps[:max_steps]

    plan["patient_id"] = patient_id
    plan["focus"] = plan.get("focus") or focus
    plan["steps"] = normalized_steps

    return plan


async def detective_report_llm(
    client: OpenAI,
    report_payload: Dict[str, Any],
) -> str:
    """
    Final EoH Detective report LLM.

    Input:
      - report_payload: {
          "high_level_question": str,
          "patient_id": str,
          "focus": str,
          "timeline_snapshot": {...},
          "steps": [ {step_summaries...} ],
        }

    Returns:
      - report_text: markdown-like string following EOH_DETECTIVE_REPORT_SYSTEM_PROMPT
    """
    resp = await _chat_completion_async(
        model=CHAT_MODEL_GUIDELINES,
        messages=[
            {
                "role": "system",
                "content": EOH_DETECTIVE_REPORT_SYSTEM_PROMPT.strip(),
            },
            {
                "role": "user",
                "content": json.dumps(
                    report_payload,
                    ensure_ascii=False,
                    cls=DateTimeJSONEncoder,
                ),
            },
        ],
        temperature=0.2,
    )

    return (resp.choices[0].message.content or "").strip()

# ---------------------------------------------------------------------------
# EoH Detective – over-arching multi-step stream
# ---------------------------------------------------------------------------

async def eoh_detective_stream_event_generator(
    *,
    request: Request,
    q: str,
    timeline_patient_id: str,
    pool: Any,
    focus: Optional[str] = None,
    max_steps: int = 6,
    # you can pass through flags that will be used for each step
    db_sources: Optional[List[str]] = None,
    limit: int = 10,
    ctx_k: int = 32,
    valyu_k: int = 3,
    with_llm: bool = True,
    llm_mode: str = "chunk",
    use_valyu: bool = True,
    valyu_mode: str = "search",
    valyu_raw: bool = True,
    valyu_sources: Optional[str] = None,
    valyu_boost: float = 1.0,
    research: int = 0,
    enable_gap: int = 1,
) -> AsyncIterator[Dict[str, str]]:
    """
    Over-arching detective stream:
      1. Create a multi-step investigation plan via eoh_detective_planner.
      2. Execute each step by calling eoh_stream_event_generator internally.
      3. Stream all intermediate SSE with step_ids embedded in data payloads,
         plus final meta and a top-level EoH Detective report.

    NOTE: This is a thin orchestrator. It delegates heavy lifting to /eoh_stream
    and only adds planning + step-level + final-report structure.
    """

    t0 = time.perf_counter()

    if not timeline_patient_id:
        yield sse(
            "error",
            {"error": "missing_timeline_patient_id", "detail": "timeline_patient_id is required"},
        )
        return

    # If db_sources not provided, fall back to your usual EoH default sources
    if db_sources is None:
        db_sources = list(EOH_STREAM_DEFAULT_SOURCES)

    # -----------------------------------------------------------------------
    # 0) Start event
    # -----------------------------------------------------------------------
    yield sse(
        "start",
        {
            "mode": "eoh_detective",
            "q": q,
            "patient_id": timeline_patient_id,
            "max_steps": max_steps,
            "db_sources": db_sources,
        },
    )

    if await request.is_disconnected():
        return

    # -----------------------------------------------------------------------
    # 1) Build timeline snapshot for planner + final report
    #     (Detective is the owner of the one-time timeline summarizer call.)
    # -----------------------------------------------------------------------
    timeline_snapshot: Optional[Dict[str, Any]] = None
    diag_payload: Optional[Dict[str, Any]] = None
    timeline_summary_for_planner: Optional[str] = None

    try:
        events = await load_patient_timeline(timeline_patient_id)
        timeline_ctx_local = await timeline_engine.build_timeline_context_from_events(
            events, timeline_patient_id
        )

        # Diagnostic landscape payload
        if timeline_ctx_local.diagnostic_landscape:
            dl = timeline_ctx_local.diagnostic_landscape
            if hasattr(dl, "to_payload") and callable(dl.to_payload):
                diag_payload = dl.to_payload()
            elif hasattr(dl, "to_normalized_dict") and callable(dl.to_normalized_dict):
                diag_payload = {"weights": dl.to_normalized_dict()}
            elif isinstance(dl, dict):
                diag_payload = dl
            else:
                diag_payload = None
        else:
            diag_payload = None

        # Landscape history
        history = timeline_engine.compute_landscape_history_from_events(
            events, timeline_patient_id
        )

        # -------------------------------------------------------------------
        # 1a) One-time timeline summarizer LLM (Detective owns this)
        # -------------------------------------------------------------------
        timeline_summaries: Optional[TimelineSummaries] = None
        try:
            # Emit a status event before we call the summarizer
            try:
                yield sse(
                    "status",
                    {
                        "status": "timeline_summarizer_start",
                        "detail": "Running timeline summarizer (PROBE+RAG or hierarchical, depending on size and flags).",
                        "patient_id": timeline_patient_id,
                        "timeline_chars": len(timeline_ctx_local.context_text or ""),
                        "event_count": len(events or []),
                    },
                )
            except Exception:
                logger.debug(
                    "eoh_detective: failed to emit timeline_summarizer_start SSE",
                    exc_info=True,
                )

            timeline_summaries = await asyncio.wait_for(
                summarize_timeline_for_eoh(
                    client=_openai_client,
                    question=q,
                    timeline_text=timeline_ctx_local.context_text,
                    pool=pool,
                    patient_id=timeline_patient_id,
                ),
                timeout=DETECTIVE_SUMMARIZER_TIMEOUT_S,
            )
        except Exception:
            logger.exception("eoh_detective: timeline summarizer failed")
            timeline_summaries = None

        # Emit SSE describing what the summarizer produced
        try:
            if timeline_summaries is not None:
                full_len = len(timeline_summaries.timeline_summary or "")
                router_len = len(timeline_summaries.timeline_summary or "")
                valyu_len = len(timeline_summaries.valyu_summary or "")
                query_terms_len = len(
                    timeline_summaries.timeline_summary or ""
                )
                meds_labs_len = len(
                    timeline_summaries.meds_and_labs_snapshot or ""
                )

                # High-level meta event
                yield sse(
                    "timeline_summarizer_result",
                    {
                        "patient_id": timeline_patient_id,
                        "full_len": full_len,
                        "router_len": router_len,
                        "valyu_len": valyu_len,
                        "query_terms_len": query_terms_len,
                        "meds_and_labs_len": meds_labs_len,
                        "has_full": bool(full_len),
                        "has_router": bool(router_len),
                        "has_valyu": bool(valyu_len),
                        "has_query_terms": bool(query_terms_len),
                        "has_meds_and_labs": bool(meds_labs_len),
                    },
                )

                # Optional: send a compact view of query-term helper text
                if timeline_summaries.timeline_summary:
                    yield sse(
                        "timeline_summarizer_query_terms",
                        {
                            "patient_id": timeline_patient_id,
                            # Trim so we don’t blow up the stream; this is for UI/debug.
                            "summary": timeline_summaries.timeline_summary[
                                :4000
                            ],
                        },
                    )

                # Optional: send meds/labs snapshot as its own event
                if timeline_summaries.meds_and_labs_snapshot:
                    yield sse(
                        "timeline_summarizer_meds_labs_snapshot",
                        {
                            "patient_id": timeline_patient_id,
                            "snapshot": timeline_summaries.meds_and_labs_snapshot[
                                :4000
                            ],
                        },
                    )

                # Small status marker so UI can show "timeline summarizer done"
                yield sse(
                    "status",
                    {
                        "status": "timeline_summarizer_done",
                        "detail": "Timeline summarizer completed.",
                        "patient_id": timeline_patient_id,
                    },
                )

        except Exception:
            logger.debug(
                "eoh_detective: failed to emit timeline summarizer SSE events",
                exc_info=True,
            )

        if await request.is_disconnected():
            return

        # Router-style summary for planner / router (fallback-safe)
        try:
            # Canonical summary for ALL downstream LLMs (router, Valyu, EoH steps)
            # TimelineSummaries already gives you a single canonical story, but we
            # defensively fall back if needed.
            canonical_summary = (
                (timeline_summaries.timeline_summary if timeline_summaries else None)
                or timeline_summary_for_planner
                or timeline_ctx_local.context_text
                or ""
            )

            if len(canonical_summary) > SUMMARY_MAX_CHARS:
                canonical_summary = canonical_summary[:SUMMARY_MAX_CHARS]

            if not canonical_summary:
                canonical_summary = timeline_ctx_local.context_text or ""

            probe_debug = getattr(timeline_summaries, "probe_debug", None) if timeline_summaries else None

            timeline_snapshot = {
                "patient_id": timeline_patient_id,
                "span_days": timeline_ctx_local.span_days,
                "key_signals": timeline_ctx_local.key_signals,
                "flare_features": timeline_ctx_local.flare_features,
                "diagnostic_landscape": diag_payload,
                "diagnostic_landscape_history": history,
                "timeline_summary": canonical_summary,
                "timeline_meds_and_labs_snapshot": (
                    timeline_summaries.meds_and_labs_snapshot if timeline_summaries else ""
                ),
            }

            if probe_debug is not None:
                timeline_snapshot["timeline_probe"] = probe_debug

            # Optional SSE for detective UI
            yield sse(
                "detective_timeline_snapshot",
                {
                    "patient_id": timeline_patient_id,
                    "span_days": timeline_ctx_local.span_days,
                    "has_diag_landscape": bool(diag_payload),
                    "has_timeline_summary": bool(canonical_summary),
                    "key_signals": timeline_ctx_local.key_signals,
                },
            )

        except Exception:
            logger.exception("eoh_detective: failed to build router-style summary for timeline snapshot")
            # Fallback: use raw context_text if available
            if timeline_ctx_local:
                canonical_summary = timeline_ctx_local.context_text or ""
                timeline_snapshot = {
                    "patient_id": timeline_patient_id,
                    "span_days": timeline_ctx_local.span_days,
                    "key_signals": timeline_ctx_local.key_signals,
                    "flare_features": timeline_ctx_local.flare_features,
                    "diagnostic_landscape": diag_payload,
                    "diagnostic_landscape_history": history,
                    "timeline_summary": canonical_summary,
                }
            else:
                timeline_snapshot = None

    except Exception:
        logger.exception("eoh_detective: failed to build timeline snapshot")
        timeline_snapshot = None
        diag_payload = None
        timeline_summary_for_planner = None

    # -----------------------------------------------------------------------
    # 1b) Load or create PatientTimelineVision for graph enrichment
    # -----------------------------------------------------------------------
    detective_vision: Optional[PatientTimelineVision] = None
    try:
        detective_vision = load_timeline_vision(timeline_patient_id)
        if not detective_vision.patient_id:
            detective_vision = PatientTimelineVision(
                patient_id=timeline_patient_id,
                built_at=datetime.utcnow().isoformat(),
                session_only=False,
                metadata={"source": "detective_run"},
            )
        logger.info(
            "eoh_detective: loaded vision graph — %d events, %d edges",
            len(detective_vision.events), detective_vision.count_edges(),
        )
        yield sse(
            "status",
            {
                "status": "vision_graph_loaded",
                "detail": f"Timeline vision graph: {len(detective_vision.events)} events, {detective_vision.count_edges()} edges",
                "patient_id": timeline_patient_id,
                "graph_events": len(detective_vision.events),
                "graph_edges": detective_vision.count_edges(),
            },
        )
    except Exception:
        logger.warning("eoh_detective: could not load vision graph, creating empty", exc_info=True)
        detective_vision = PatientTimelineVision(
            patient_id=timeline_patient_id,
            built_at=datetime.utcnow().isoformat(),
            session_only=False,
            metadata={"source": "detective_run"},
        )

    # -----------------------------------------------------------------------
    # 2) Plan creation (planner sees timeline snapshot)
    # -----------------------------------------------------------------------
    focus_label = focus or "eoh_detective_run"

    yield sse(
        "status",
        {
            "status": "planning",
            "detail": "Creating EoH detective plan",
            "patient_id": timeline_patient_id,
        },
    )

    try:
        plan = await asyncio.wait_for(
            eoh_detective_planner(
                client=_openai_client,
                patient_id=timeline_patient_id,
                focus=focus_label,
                high_level_question=q,
                max_steps=max_steps,
                patient_snapshot=timeline_snapshot,
            ),
            timeout=DETECTIVE_PLANNER_TIMEOUT_S,
        )
    except Exception as e:
        logger.exception("eoh_detective: planner failed")
        yield sse(
            "error",
            {"error": "planner_failed", "detail": str(e)},
        )
        return

    steps = plan.get("steps") or []

    yield sse(
        "detective_plan",
        {
            "patient_id": plan.get("patient_id"),
            "focus": plan.get("focus"),
            "steps": [
                {
                    "step_id": s["step_id"],
                    "kind": s["kind"],
                    "question_type": s["question_type"],
                    "debug": s.get("debug", False),
                }
                for s in steps
            ],
        },
    )

    if await request.is_disconnected():
        return

    # -----------------------------------------------------------------------
    # 3) Execute steps sequentially
    # -----------------------------------------------------------------------
    detective_meta: Dict[str, Any] = {
        "patient_id": timeline_patient_id,
        "focus": plan.get("focus"),
        "n_steps": len(steps),
        "step_summaries": [],
    }

    for step in steps:
        step_id = step["step_id"]
        step_q = step["q"]
        step_debug = bool(step.get("debug", False))

        # Step start marker (top-level SSE from detective)
        yield sse(
            "detective_step_start",
            {
                "step_id": step_id,
                "kind": step["kind"],
                "question_type": step["question_type"],
                "q": step_q,
            },
        )

        if await request.is_disconnected():
            return

        step_citations = None
        step_meta = None
        step_answer_buffer: List[str] = []

        # Build a compact, router-safe patient_state JSON
        compact_patient_state = (
            build_compact_patient_state_for_router(timeline_snapshot)
            if timeline_snapshot
            else None
        )

        # Inner EoH stream generator
        inner_gen = eoh_stream_event_generator(
            request=request,
            q=step_q,
            db_sources=db_sources,
            limit=limit,
            ctx_k=ctx_k,
            valyu_k=valyu_k,
            with_llm=with_llm,
            llm_mode=llm_mode,
            use_valyu=use_valyu,
            valyu_mode=valyu_mode,
            valyu_raw=valyu_raw,
            valyu_sources=valyu_sources,
            valyu_boost=valyu_boost,
            pool=pool,
            patient_state=compact_patient_state,
            debug=step_debug,
            use_timeline=True,
            timeline_patient_id=timeline_patient_id,
            research=research,
            enable_gap=enable_gap,
        )

        step_t0 = time.perf_counter()
        step_timed_out = False
        while True:
            elapsed_s = int(time.perf_counter() - step_t0)
            if elapsed_s > DETECTIVE_STEP_MAX_TIMEOUT_S:
                step_timed_out = True
                yield sse(
                    "error",
                    {
                        "error": "detective_step_timeout",
                        "detail": f"Step {step_id} exceeded max duration",
                        "step_id": step_id,
                        "elapsed_s": elapsed_s,
                        "max_s": DETECTIVE_STEP_MAX_TIMEOUT_S,
                    },
                )
                break

            try:
                ev = await asyncio.wait_for(
                    inner_gen.__anext__(),
                    timeout=DETECTIVE_STEP_IDLE_TIMEOUT_S,
                )
            except StopAsyncIteration:
                break
            except asyncio.TimeoutError:
                # Explicit progress pulse so clients don't see endless opaque pings.
                yield sse(
                    "status",
                    {
                        "status": "detective_step_still_running",
                        "detail": f"Step {step_id} still running",
                        "step_id": step_id,
                        "elapsed_s": elapsed_s,
                    },
                )
                continue

            # ev is {"event": ..., "data": "..."} from sse()
            wrapped_ev = dict(ev)
            wrapped_ev.setdefault("event", "")
            wrapped_ev.setdefault("data", "")

            # Try to read data as JSON once so we can both intercept and annotate it
            data_obj = None
            data_str = wrapped_ev["data"]

            if isinstance(data_str, str) and data_str:
                try:
                    data_obj = json.loads(data_str)
                except Exception:
                    data_obj = None

            # Intercept citations/meta for detective summary
            try:
                if wrapped_ev["event"] == "citations" and isinstance(data_obj, dict):
                    step_citations = data_obj.get("citations")
                elif wrapped_ev["event"] == "end" and isinstance(data_obj, dict):
                    step_meta = data_obj.get("meta")
            except Exception:
                logger.debug(
                    "eoh_detective: failed to parse inner event for summary",
                    exc_info=True,
                )

            # Collect LLM answer tokens for opportunistic graph enrichment
            try:
                ev_name = wrapped_ev.get("event", "")
                if ev_name.startswith("llm") and isinstance(data_obj, dict):
                    chunk = (
                        data_obj.get("text")
                        or data_obj.get("delta")
                        or data_obj.get("content")
                        or ""
                    )
                    if isinstance(chunk, str) and chunk:
                        step_answer_buffer.append(chunk)
            except Exception:
                pass

            # Inject step_id into *data payload*, not as top-level SSE kwarg
            if isinstance(data_obj, dict):
                data_obj.setdefault("step_id", step_id)
                wrapped_ev["data"] = json.dumps(data_obj, ensure_ascii=False)

            yield wrapped_ev

            if await request.is_disconnected():
                return

        # Ensure inner stream is closed on timeout/break.
        if step_timed_out:
            try:
                await inner_gen.aclose()
            except Exception:
                pass

        # Per-step detective summary
        step_answer_text = "".join(step_answer_buffer).strip()

        detective_meta["step_summaries"].append(
            {
                "step_id": step_id,
                "kind": step["kind"],
                "planner_question_type": step["question_type"],
                "router_question_type": (step_meta or {}).get("question_type"),
                "q": step_q,
                "citations": step_citations,
                "meta": step_meta,
            }
        )

        # Step end marker (top-level SSE)
        yield sse(
            "detective_step_end",
            {
                "step_id": step_id,
                "citations_present": bool(step_citations),
                "has_meta": step_meta is not None,
            },
        )

        # ---------------------------------------------------------------
        # 3b) Opportunistic graph enrichment after each step
        # ---------------------------------------------------------------
        if detective_vision is not None and step_answer_text:
            try:
                yield sse(
                    "status",
                    {
                        "status": "graph_enrichment_start",
                        "detail": f"Opportunistic graph enrichment for step {step_id}",
                        "step_id": step_id,
                        "patient_id": timeline_patient_id,
                    },
                )

                enrich_stats = await asyncio.wait_for(
                    enrich_graph_opportunistic(
                        step_id=step_id,
                        step_question=step_q,
                        step_answer=step_answer_text,
                        step_citations=step_citations,
                        patient_id=timeline_patient_id,
                        vision=detective_vision,
                    ),
                    timeout=DETECTIVE_ENRICH_TIMEOUT_S,
                )

                yield sse(
                    "graph_enrichment_result",
                    {
                        "step_id": step_id,
                        "patient_id": timeline_patient_id,
                        "events_added": enrich_stats.get("events_added", 0),
                        "edges_added": enrich_stats.get("edges_added", 0),
                        "graph_events_total": len(detective_vision.events),
                        "graph_edges_total": detective_vision.count_edges(),
                        "elapsed_ms": enrich_stats.get("elapsed_ms", 0),
                        "error": enrich_stats.get("error"),
                    },
                )

                logger.info(
                    "eoh_detective: graph enrichment step=%s +%d events +%d edges (total: %d events, %d edges)",
                    step_id,
                    enrich_stats.get("events_added", 0),
                    enrich_stats.get("edges_added", 0),
                    len(detective_vision.events),
                    detective_vision.count_edges(),
                )

            except Exception:
                logger.warning(
                    "eoh_detective: opportunistic enrichment failed for step %s",
                    step_id,
                    exc_info=True,
                )

        if await request.is_disconnected():
            return
    # -----------------------------------------------------------------------
    # 3c) Save enriched vision graph after all steps
    # -----------------------------------------------------------------------
    if detective_vision is not None:
        try:
            save_timeline_vision(detective_vision)
            logger.info(
                "eoh_detective: saved vision graph — %d events, %d edges",
                len(detective_vision.events), detective_vision.count_edges(),
            )
            yield sse(
                "status",
                {
                    "status": "vision_graph_saved",
                    "detail": f"Vision graph saved: {len(detective_vision.events)} events, {detective_vision.count_edges()} edges",
                    "patient_id": timeline_patient_id,
                    "graph_events": len(detective_vision.events),
                    "graph_edges": detective_vision.count_edges(),
                },
            )
        except Exception:
            logger.warning("eoh_detective: failed to save vision graph", exc_info=True)

    # -----------------------------------------------------------------------
    # 4) Final detective meta + timing
    # -----------------------------------------------------------------------
    elapsed_ms = int((time.perf_counter() - t0) * 1000)

    graph_state = {}
    if detective_vision is not None:
        graph_state = {
            "graph_events": len(detective_vision.events),
            "graph_edges": detective_vision.count_edges(),
        }

    yield sse(
        "detective_summary",
        {
            "patient_id": detective_meta["patient_id"],
            "focus": detective_meta["focus"],
            "n_steps": detective_meta["n_steps"],
            "elapsed_ms": elapsed_ms,
            "steps": detective_meta["step_summaries"],
            **graph_state,
        },
    )

    if await request.is_disconnected():
        return

    # -----------------------------------------------------------------------
    # 5) Generate final detective report (final EoH Detective LLM)
    # -----------------------------------------------------------------------
    if with_llm:
        try:
            report_payload = {
                "high_level_question": q,
                "patient_id": timeline_patient_id,
                "focus": detective_meta["focus"],
                "timeline_snapshot": timeline_snapshot,
                "steps": detective_meta["step_summaries"],
            }

            yield sse(
                "status",
                {
                    "status": "detective_llm_reporting",
                    "detail": "Generating final EoH Detective report",
                    "patient_id": timeline_patient_id,
                },
            )

            report_text = await asyncio.wait_for(
                detective_report_llm(
                    _openai_client,
                    report_payload,
                ),
                timeout=DETECTIVE_REPORT_TIMEOUT_S,
            )

            yield sse(
                "detective_report",
                {
                    "patient_id": timeline_patient_id,
                    "focus": detective_meta["focus"],
                    "report": report_text,
                },
            )

        except Exception:
            logger.exception("eoh_detective: final report generation failed")
            yield sse(
                "status",
                {
                    "status": "detective_llm_error",
                    "detail": "Failed to generate final detective report",
                },
            )

    # Final end marker
    yield sse(
        "end",
        {
            "meta": {
                "mode": "eoh_detective",
                "patient_id": timeline_patient_id,
                "focus": detective_meta["focus"],
                "n_steps": detective_meta["n_steps"],
                "elapsed_ms": elapsed_ms,
            }
        },
    )

# ---------------------------------------------------------------------------
# EoH Detective Stream
# ---------------------------------------------------------------------------

@router.post("/eoh_detective_stream")
async def eoh_detective_stream(
    request: Request,
    body: EohDetectiveStreamRequest,
    pool: Any = Depends(resolve_pg_pool),
):
    """
    Detective wrapper endpoint.
    Supports both canonical params:
      - q, timeline_patient_id
    and friendly aliases:
      - question, patient_id
    
    Privacy: POST body prevents query logging in URLs/reverse proxies.
    Anonymized query logged for visibility (no PII/PHI).
    """
    
    # Start anonymization in parallel (non-blocking) - use q or question, whichever is available
    query_text = (body.q or body.question or "").strip()
    if query_text:
        anon_task = asyncio.create_task(anonymize_query_for_logging(query_text))
    else:
        anon_task = None

    # ----------------------------
    # Normalize aliases
    # ----------------------------
    q_final = query_text
    pid_final = (body.timeline_patient_id or body.patient_id or "").strip()

    # allow old "use_gap" param to override enable_gap
    enable_gap = body.enable_gap
    if body.use_gap is not None:
        enable_gap = int(body.use_gap)

    if not q_final:
        raise HTTPException(
            status_code=422,
            detail="Missing required query param: q (or alias question)",
        )
    if not pid_final:
        raise HTTPException(
            status_code=422,
            detail="Missing required query param: timeline_patient_id (or alias patient_id)",
        )
    
    # Extract other parameters from body
    focus = (body.focus or "").strip() or None
    sources = (body.sources or "").strip() or None
    max_steps = body.max_steps
    limit = body.limit
    ctx_k = body.ctx_k
    valyu_k = body.valyu_k
    use_valyu = body.use_valyu
    valyu_mode = (body.valyu_mode or "search").strip()
    valyu_raw = body.valyu_raw
    valyu_sources = body.valyu_sources
    valyu_boost = body.valyu_boost
    with_llm = body.with_llm
    llm_mode = (body.llm_mode or "chunk").strip()
    research = body.research
    
    # Parse sources similar to your existing eoh_stream route
    if sources:
        db_sources = [s.strip() for s in sources.split(",") if s.strip()]
    else:
        db_sources = list(EOH_STREAM_DEFAULT_SOURCES)
    
    # Get anonymized query for logging (with timeout fallback)
    if anon_task:
        try:
            anon_query = await asyncio.wait_for(anon_task, timeout=0.5)
        except asyncio.TimeoutError:
            anon_query = "query_received: anonymization_still_processing"
    else:
        anon_query = "query_received: no_query_text"
    
    # Log with anonymized query (privacy-safe)
    logger.info(f"Query: {anon_query}, endpoint: /eoh_detective_stream, patient_id: [REDACTED], max_steps: {max_steps}")

    gen = eoh_detective_stream_event_generator(
        request=request,
        q=q_final,
        timeline_patient_id=pid_final,
        pool=pool,
        focus=focus,
        max_steps=max_steps,
        db_sources=db_sources,
        limit=limit,
        ctx_k=ctx_k,
        valyu_k=valyu_k,
        with_llm=with_llm,
        llm_mode=llm_mode,
        use_valyu=use_valyu,
        valyu_mode=valyu_mode,
        valyu_raw=valyu_raw,
        valyu_sources=valyu_sources,
        valyu_boost=valyu_boost,
        research=research,
        enable_gap=enable_gap,
    )
    return EventSourceResponse(gen, media_type="text/event-stream")


@router.get("/eoh_detective_stream")
async def eoh_detective_stream_get(
    request: Request,
    q: str = "",
    question: str = "",
    patient_id: str = "",
    timeline_patient_id: str = "",
    sources: str = "",
    focus: str = "",
    max_steps: int = 6,
    limit: int = 10,
    ctx_k: int = 32,
    with_llm: bool = True,
    research: int = 1,
    enable_gap: int = 1,
    use_valyu: bool = False,
    valyu_raw: bool = False,
    pool: Any = Depends(resolve_pg_pool),
):
    """GET alias for /eoh_detective_stream (curl-friendly with query params)."""
    body = EohDetectiveStreamRequest(
        q=q or question or None,
        question=question or None,
        patient_id=patient_id or None,
        timeline_patient_id=timeline_patient_id or None,
        sources=sources or None,
        focus=focus or None,
        max_steps=max_steps,
        limit=limit,
        ctx_k=ctx_k,
        with_llm=with_llm,
        research=research,
        enable_gap=enable_gap,
        use_valyu=use_valyu,
        valyu_raw=valyu_raw,
    )
    return await eoh_detective_stream(request, body, pool)