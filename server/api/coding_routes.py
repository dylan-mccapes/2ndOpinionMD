# server/api/coding_routes.py
# Defines request models to avoid Pydantic forward-ref error and uses citation_utils helpers.

from __future__ import annotations
import os, json, re, io, textwrap
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, Query, Body, Request
from fastapi.responses import Response
from pydantic import BaseModel
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors

from .rag_routes import _handle_rag_ask
from .citation_utils import (
    choose_citation, split_matches_by_role, enrich_missing_code_from_matches, explain_missing_citation
)

router = APIRouter(prefix="/api/rag", tags=["coding"])

class CodingRequest(BaseModel):
    note: str
    sources: Optional[str] = None
    limit: Optional[int] = 60

# ------- helpers (identical to what you have; trimmed for brevity) -------
_CODE_KEYS = ("system","code","title","why","evidence_titles")
_LAB_KEYS  = ("system","code","title","purpose","evidence_titles")
_MED_KEYS  = ("system","code","title","indication","evidence_titles")
def _strip_code_fences(s: Optional[str]) -> str:
    if not s: return ""
    s = s.strip()
    if s.startswith("```"):
        s = re.sub(r"^```(?:json|JSON)?\s*", "", s); s = re.sub(r"\s*```$", "", s)
    return s.strip()
def _parse_model_json(text: Optional[str]) -> Dict[str, Any]:
    if not text: return {"_parse_error": "empty ai_response", "_raw": ""}
    try: return json.loads(_strip_code_fences(text))
    except Exception as e: return {"_parse_error": f"{e}", "_raw": text}
def _ensure_list(x: Any) -> List[Any]: return x if isinstance(x, list) else ([] if x is None else [x])
def _norm_item(it: Any, kind: str) -> Dict[str, Any]:
    d = dict(it) if isinstance(it, dict) else {"title": str(it)}
    keys = _CODE_KEYS if kind=="code" else (_LAB_KEYS if kind=="lab" else _MED_KEYS if kind=="med" else ("title","evidence_titles"))
    for k in (keys if isinstance(keys, tuple) else keys):
        d.setdefault(k, "" if k != "evidence_titles" else [])
    ev = d.get("evidence_titles", []); ev = [str(t).strip() for t in (ev if isinstance(ev, list) else [ev]) if str(t).strip()]
    d["evidence_titles"] = ev; return d
def _coerce_blocks(J: Dict[str, Any]) -> Dict[str, Any]:
    for key, kind in (("probable_dx","code"),("differential_dx","code"),("procedures","code"),("labs","lab"),("medications","med")):
        J[key] = [_norm_item(it, kind) for it in _ensure_list(J.get(key, []))]
    return J
def _excerpt(text: str, needle: str, limit: int = 360) -> str:
    if not text: return ""
    text = re.sub(r"\s+", " ", text).strip()
    i = text.lower().find((needle or "").lower())
    start = max(0, (i if i>=0 else 0) - 120); end = min(len(text), (i+len(needle) if i>=0 else limit) + 120)
    return text[start:end][:limit]
def _mk_table(data: List[List[str]], max_width: float) -> Table:
    if not data: return Table([["(no data)"]])
    lens = [max(len(str(row[i])) for row in data) for i in range(len(data[0]))]
    total = float(sum(lens) or 1.0); col_widths = [max(40.0, max_width * (L/total)) for L in lens]
    t = Table(data, colWidths=col_widths, repeatRows=1)
    t.setStyle(TableStyle([("ALIGN",(0,0),(-1,-1),"LEFT"),("BACKGROUND",(0,0),(-1,0),colors.lightgrey),("GRID",(0,0),(-1,-1),0.25,colors.grey),("FONTNAME",(0,0),(-1,0),"Helvetica-Bold"),("VALIGN",(0,0),(-1,-1),"TOP")]))
    return t
def _csv_bytes(payload: Dict[str, Any]) -> bytes:
    import csv
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=["kind","system","code","title","why_or_indication","citation.source","citation.doc_key","citation.title","excerpt","citation_reason"])
    w.writeheader()
    def add(kind, arr, why_field):
        for it in arr or []:
            enrich_missing_code_from_matches(it, payload.get("matches") or [])
            cite, reason = choose_citation(it, payload.get("matches") or [])
            w.writerow({
                "kind":kind, "system":it.get("system",""), "code":it.get("code",""), "title":it.get("title",""),
                "why_or_indication":it.get(why_field,""), "citation.source":(cite or {}).get("source",""),
                "citation.doc_key":((cite or {}).get("meta") or {}).get("doc_key") or (cite or {}).get("source_id",""),
                "citation.title":(cite or {}).get("title",""),
                "excerpt":_excerpt((cite or {}).get("text",""), it.get("title","")),
                "citation_reason":reason if cite else explain_missing_citation(it, payload.get("matches") or [])
            })
    add("probable_dx", payload.get("probable_dx"), "why")
    add("differential_dx", payload.get("differential_dx"), "why")
    add("procedures", payload.get("procedures"), "why")
    add("labs", payload.get("labs"), "purpose")
    add("medications", payload.get("medications"), "indication")
    return buf.getvalue().encode("utf-8")
def _pdf_bytes(payload: Dict[str, Any]) -> bytes:
    buf = io.BytesIO(); doc = SimpleDocTemplate(buf, pagesize=LETTER, title="RAG Coding Report")
    styles = getSampleStyleSheet(); story: List[Any] = []
    def H(t): story.append(Paragraph(f"<b>{t}</b>", styles["Heading2"]))
    def P(t): story.append(Paragraph(textwrap.fill(str(t), width=110), styles["BodyText"]))
    def SP(h=8): story.append(Spacer(1,h))
    story.append(Paragraph("RAG Coding Report", styles["Title"])); SP(4)
    J = payload.get("insight") or {}
    if isinstance(J, dict) and J.get("assessment"): H("Clinical Insight"); P(J["assessment"]); SP()
    max_w = doc.width
    def table_for(title, arr, cols, labels):
        arr = arr or []; 
        if not arr: return
        H(title); SP(2); data = [labels]
        for it in arr:
            enrich_missing_code_from_matches(it, payload.get("matches") or [])
            data.append([str(it.get(c,"")) for c in cols])
        story.append(_mk_table(data, max_w)); SP()
    table_for("Probable Diagnoses", payload.get("probable_dx"), ["system","code","title","why"], ["System","Code","Title","Why"])
    table_for("Differential Diagnoses", payload.get("differential_dx"), ["system","code","title","why"], ["System","Code","Title","Why"])
    table_for("Procedures", payload.get("procedures"), ["system","code","title","why"], ["System","Code","Title","Why"])
    table_for("Labs", payload.get("labs"), ["system","code","title","purpose"], ["System","Code","Title","Purpose"])
    table_for("Medications", payload.get("medications"), ["system","code","title","indication"], ["System","Code","Title","Indication"])
    H("Code-by-Code Justifications"); SP(2)
    for bucket, label, why_key in (("probable_dx","Probable","why"),("differential_dx","Differential","why"),("procedures","Procedure","why"),("labs","Lab","purpose"),("medications","Medication","indication")):
        for it in payload.get(bucket) or []:
            P(f"<b>{label}:</b> " + " · ".join([x for x in [it.get('system'),it.get('code'),it.get('title')] if x]))
            why = it.get(why_key,"");  
            if why: P(f"Why: {why}")
            cite, reason = choose_citation(it, payload.get("matches") or [])
            if cite:
                dk = ((cite.get("meta") or {}).get("doc_key")) or cite.get("source_id","")
                P(f"Citation: {cite.get('source','')} :: {dk} — {cite.get('title','')}")
                P("Excerpt: " + _excerpt(cite.get("text",""), it.get("title","")))
            else:
                P(f"Citation: (pending) — {explain_missing_citation(it, payload.get('matches') or [])}")
            SP(6)
    note = payload.get("note") or ""
    if note: H("Appendix: Original Clinical Note"); SP(2); P(note); SP(4)
    doc.build(story); return buf.getvalue()

@router.post("/coding")
async def coding(
    request: Request,
    payload: CodingRequest = Body(...),
    format: str = Query("json", pattern="^(json|csv|pdf)$"),
    pretty: int = Query(0)
):
    note = (payload.note or "").strip()
    sources = payload.sources
    limit = int(payload.limit or 60)

    rag = await _handle_rag_ask(q=note, k=limit, sources_csv=sources, debug=0)
    matches = rag.get("matches") or []

    from openai import OpenAI
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    model_used = os.getenv("CHAT_MODEL", "gpt-4o-mini")

    PROMPT = f"""
You are a clinical assistant. Return STRICT JSON ONLY (no code fences). Schema:
{{"insight": {{"assessment": "2-4 sentences","risk_factors": [],"red_flags": [],"lifestyle_plan": [],"follow_up": []}},
 "probable_dx": [{{"system":"ICD-10-CM","code":"","title":"","why":"","evidence_titles":[]}}],
 "differential_dx": [{{"system":"ICD-10-CM","code":"","title":"","why":"","evidence_titles":[]}}],
 "procedures": [{{"system":"ICD-10-PCS","code":"","title":"","why":"","evidence_titles":[]}}],
 "labs": [{{"system":"LOINC","code":"","title":"","purpose":"","evidence_titles":[]}}],
 "medications": [{{"system":"RxNorm","code":"","title":"","indication":"","evidence_titles":[]}}],
 "patient_education": [{{"topic":"","evidence_titles":[]}}], "notes": ""}}
Rules:
- Only include items if a specific authoritative document is present in evidence; otherwise omit.
- Prefer ICD-10-CM/PCS; include ICD-11/SNOMED only if retrieved.
Clinical note:
{note}
""".strip()

    try:
        resp = client.chat.completions.create(
            model=model_used,
            response_format={"type":"json_object"},
            temperature=0.1,
            messages=[
                {"role":"system","content":"You are a careful clinical assistant. Output must be a single JSON object."},
                {"role":"user","content":PROMPT + "\n\nUse only these retrieved evidence snippets."},
                {"role":"user","content":"Evidence snippets:\n" + "\n\n".join(
                    f"[{i+1}] {(it.get('source') or 'unknown')} — {(it.get('title') or 'Untitled')}\n{(it.get('text') or '')[:800]}..."
                    for i, it in enumerate(matches[:6])
                )}
            ],
        )
        model_text = (resp.choices[0].message.content or "").strip()
    except Exception:
        model_text = ""

    J = _coerce_blocks(_parse_model_json(model_text))
    payload_out = {**J, "matches": matches, "ai_model": model_used, "note": note}

    if format == "csv":
        return Response(content=_csv_bytes(payload_out), media_type="text/csv",
                        headers={"Content-Disposition":"attachment; filename=coding.csv"})
    if format == "pdf":
        return Response(content=_pdf_bytes(payload_out), media_type="application/pdf",
                        headers={"Content-Disposition":"attachment; filename=coding.pdf"})
    return Response(content=json.dumps(payload_out, indent=(2 if pretty else None)), media_type="application/json")
