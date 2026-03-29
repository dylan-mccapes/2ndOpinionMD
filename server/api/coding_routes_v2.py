# server/api/coding_routes_v2.py
from __future__ import annotations
import os, io, json, re, textwrap
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Query, Body, Request
from fastapi.responses import Response
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib import colors

from .rag_routes import _handle_rag_ask
from .stream_config import CHAT_MODEL_CODING_CORE
from .citation_governance import compose_claim_bundle, compute_col_widths

router = APIRouter(prefix="/api/rag", tags=["coding-v2"])

_CODE_KEYS = ("system","code","title","why","evidence_titles")
_LAB_KEYS  = ("system","code","title","purpose","evidence_titles")
_MED_KEYS  = ("system","code","title","indication","evidence_titles")

def _strip_fences(s: Optional[str]) -> str:
    if not s: return ""
    s = s.strip()
    if s.startswith("```"):
        s = re.sub(r"^```(?:json|JSON)?\s*", "", s)
        s = re.sub(r"\s*```$", "", s)
    return s.strip()

def _parse_json(text: Optional[str]) -> Dict[str,Any]:
    if not text: return {}
    try:
        return json.loads(_strip_fences(text))
    except Exception:
        return {}

def _ensure_list(x: Any) -> List[Any]:
    if x is None: return []
    if isinstance(x, list): return x
    return [x]

def _norm_item(it: Any, kind: str) -> Dict[str, Any]:
    d = dict(it) if isinstance(it, dict) else {"title": str(it)}
    if kind == "code":
        for k in _CODE_KEYS: d.setdefault(k, "" if k != "evidence_titles" else [])
    elif kind == "lab":
        for k in _LAB_KEYS: d.setdefault(k, "" if k != "evidence_titles" else [])
    elif kind == "med":
        for k in _MED_KEYS: d.setdefault(k, "" if k != "evidence_titles" else [])
    ev = d.get("evidence_titles", [])
    if isinstance(ev, str): ev = [ev]
    d["evidence_titles"] = [str(t).strip() for t in (ev or []) if str(t).strip()]
    return d

def _coerce_blocks(J: Dict[str, Any]) -> Dict[str, Any]:
    for key, kind in (
        ("probable_dx","code"),
        ("differential_dx","code"),
        ("procedures","code"),
        ("labs","lab"),
        ("medications","med"),
    ):
        J[key] = [_norm_item(it, kind) for it in _ensure_list(J.get(key, []))]
    return J

async def _backfill_authority(items: List[Dict[str,Any]], matches: List[Dict[str,Any]], system: str) -> None:
    """
    If a code is missing, do a one-shot ontology lookup by title to fetch
    an authoritative document (keeps RxNorm/LOINC filled).
    """
    for it in [i for i in items if not (i.get("code") or "").strip()]:
        title = (it.get("title") or "").strip()
        if not title: continue
        res = await _handle_rag_ask(q=title, k=1, sources_csv=system, debug=0)
        mm = res.get("matches") or []
        if mm:
            m = mm[0]
            it["system"] = system.upper() if system != "snomed" else "SNOMED"
            it["code"] = m.get("source_id") or ""
            if not it.get("title"): it["title"] = m.get("title") or ""
            matches.append(m)  # include for evidence

def _rows_for_csv(bundles: List[Dict[str,Any]]) -> List[Dict[str,str]]:
    rows = []
    for b in bundles:
        codes = b.get("codes") or {}
        rows.append({
            "kind": b.get("kind",""),
            "claim": b.get("claim",""),
            "icd10cm": (codes.get("icd10cm") or {}).get("code",""),
            "icd11":   (codes.get("icd11") or {}).get("code",""),
            "snomed":  (codes.get("snomed") or {}).get("code",""),
            "loinc":   (codes.get("loinc") or {}).get("code",""),
            "rxnorm":  (codes.get("rxnorm") or {}).get("code",""),
            "evidence_count": str(len(b.get("evidence") or [])),
            "mapping_edges": str(len(b.get("mappings") or [])),
            "status": b.get("status","")
        })
    return rows

def _csv_bytes(rows: List[Dict[str,str]]) -> bytes:
    import csv
    buf = io.StringIO()
    fieldnames = ["kind","claim","icd10cm","icd11","snomed","loinc","rxnorm","evidence_count","mapping_edges","status"]
    w = csv.DictWriter(buf, fieldnames=fieldnames)
    w.writeheader()
    for r in rows: w.writerow(r)
    return buf.getvalue().encode("utf-8")

def _pdf_bytes(note: str, bundles: List[Dict[str,Any]]) -> bytes:
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=LETTER, title="RAG Coding Report")
    styles = getSampleStyleSheet()
    story: List[Any] = []

    def H(txt): story.append(Paragraph(f"<b>{txt}</b>", styles["Heading2"]))
    def P(txt): story.append(Paragraph(textwrap.fill(txt, width=110), styles["BodyText"]))
    def SP(h=8): story.append(Spacer(1, h))

    story.append(Paragraph("RAG Coding Report", styles["Title"])); SP(6)

    # Summary table (left-aligned, fitted to page width)
    data = [["Kind","Claim","ICD-10-CM","ICD-11","SNOMED","LOINC","RxNorm","Evidence","Edges","Status"]]
    for b in bundles:
        codes = b.get("codes") or {}
        data.append([
            b.get("kind",""),
            b.get("claim",""),
            (codes.get("icd10cm") or {}).get("code",""),
            (codes.get("icd11") or {}).get("code",""),
            (codes.get("snomed") or {}).get("code",""),
            (codes.get("loinc") or {}).get("code",""),
            (codes.get("rxnorm") or {}).get("code",""),
            str(len(b.get("evidence") or [])),
            str(len(b.get("mappings") or [])),
            b.get("status",""),
        ])
    col_widths = compute_col_widths(data, max_width=doc.width, min_width=48.0)
    tbl = Table(data, colWidths=col_widths, repeatRows=1)
    tbl.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(-1,0), colors.lightgrey),
        ("GRID",(0,0),(-1,-1), 0.25, colors.grey),
        ("FONTNAME",(0,0),(-1,0), "Helvetica-Bold"),
        ("VALIGN",(0,0),(-1,-1), "TOP"),
        ("ALIGN",(0,0),(-1,-1), "LEFT"),
    ]))
    story.append(tbl); SP(10)

    # Justifications
    H("Code-by-Code Justifications"); SP(4)
    for b in bundles:
        codes = b.get("codes") or {}
        line = " | ".join(filter(None,[
            (codes.get("icd10cm") or {}).get("code",""),
            (codes.get("icd11") or {}).get("code",""),
            (codes.get("snomed") or {}).get("code",""),
            (codes.get("loinc") or {}).get("code",""),
            (codes.get("rxnorm") or {}).get("code",""),
        ]))
        P(f"<b>{b.get('kind','')}</b> — {b.get('claim','')}")
        if line: P(f"Codes: {line}")
        ev = b.get("evidence") or []
        for e in ev[:3]:
            if e.get("type") == "guideline":
                P(f"Guideline: {e.get('source')} {e.get('doc')} {e.get('section')}: “{e.get('quote','')}”")
            elif e.get("type") == "ontology":
                P(f"Ontology: {e.get('source')}::{e.get('code')} — {e.get('title')}: “{e.get('quote','')}”")
            elif e.get("type") == "lexical":
                P(f"Lexical: {e.get('label')} ({e.get('cui')})")
        status = b.get("status")
        if status: P(f"Status: {status}")
        SP(8)

    # Appendix — Original Note
    story.append(PageBreak())
    story.append(Paragraph("Appendix A — Original Clinical Note", styles["Heading1"])); SP(6)
    story.append(Paragraph(textwrap.fill(note or "", width=100), styles["BodyText"]))

    doc.build(story)
    return buf.getvalue()

@router.post("/coding")
async def coding(request: Request, payload: Dict[str, Any] = Body(...),
                 format: str = Query("json", pattern="^(json|csv|pdf)$"),
                 pretty: int = Query(0)):
    """
    Body: { note, sources?, limit? }
    Governance: Andras v1.0
    """
    note = (payload.get("note") or "").strip()
    sources = payload.get("sources")
    limit = int(payload.get("limit") or 60)

    # RAG retrieval
    rag = await _handle_rag_ask(q=note, k=limit, sources_csv=sources, debug=0)
    matches = rag.get("matches") or []

    # Ask the model for structured items (STRICT JSON via response_format)
    model_text = "{}"
    try:
        from openai import OpenAI
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        model_used = CHAT_MODEL_CODING_CORE
        PROMPT = f"""You are a clinical assistant. Return STRICT JSON ONLY (no code fences).
Schema {{
  "probable_dx": [{{"system":"ICD-10-CM","code":"","title":"","why":"","evidence_titles":["..."]}}],
  "differential_dx": [{{"system":"ICD-10-CM","code":"","title":"","why":"","evidence_titles":["..."]}}],
  "procedures": [{{"system":"ICD-10-PCS","code":"","title":"","why":"","evidence_titles":["..."]}}],
  "labs": [{{"system":"LOINC","code":"","title":"","purpose":"","evidence_titles":["..."]}}],
  "medications": [{{"system":"RxNorm","code":"","title":"","indication":"","evidence_titles":["..."]}}]
}}
Rules:
- Only include items if their specific document was retrieved or can be looked up by exact title via the ontology source.
- Prefer SNOMED + ICD-10-CM; add ICD-11 when a concrete code/URI is retrieved. No placeholders.
- CHV is lexical only.
Clinical note:
{note}
Evidence snippets:
""" + "\n\n".join(
    f"[{i+1}] {(it.get('source') or 'unknown')} — {(it.get('title') or 'Untitled')}\n{(it.get('text') or '')[:800]}..."
    for i, it in enumerate(matches[:6])
)
        resp = client.chat.completions.create(
            model=model_used,
            response_format={"type": "json_object"},
            temperature=0.1,
            messages=[
                {"role":"system","content":"Output must be a single JSON object."},
                {"role":"user","content":PROMPT},
            ],
        )
        model_text = (resp.choices[0].message.content or "").strip()
    except Exception:
        pass

    J = _coerce_blocks(_parse_json(model_text))

    # Backfill RxNorm & LOINC if codes are missing by single-shot ontology lookups
    await _backfill_authority(J.get("medications") or [], matches, "rxnorm")
    await _backfill_authority(J.get("labs") or [], matches, "loinc")

    # Build bundles
    bundles: List[Dict[str,Any]] = []
    for bucket_key, kind in (
        ("probable_dx","probable_dx"),
        ("differential_dx","differential_dx"),
        ("procedures","procedure"),
        ("labs","lab"),
        ("medications","medication"),
    ):
        for it in (J.get(bucket_key) or []):
            b = compose_claim_bundle(kind, it, matches, retrieved_versions=rag.get("source_versions"))
            b["kind"] = kind
            # If an ICD-11 wasn’t concretely retrieved for dx/proc, mark mapping_pending per governance
            if kind in {"probable_dx","differential_dx","procedure"} and "icd11" not in (b.get("codes") or {}):
                b["status"] = "mapping_pending"
            bundles.append(b)

    out = {"bundles": bundles, "matches": matches, "ai_model": CHAT_MODEL_CODING_CORE, "note": note}

    if format == "csv":
        rows = _rows_for_csv(bundles)
        return Response(content=_csv_bytes(rows), media_type="text/csv",
                        headers={"Content-Disposition":"attachment; filename=coding.csv"})
    if format == "pdf":
        return Response(content=_pdf_bytes(note, bundles), media_type="application/pdf",
                        headers={"Content-Disposition":"attachment; filename=coding.pdf"})

    body = json.dumps(out, indent=(2 if pretty else None))
    return Response(content=body, media_type="application/json")

