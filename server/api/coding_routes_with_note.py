# server/api/coding_routes.py (with Note appended to PDF + minor fixes)
# --- add imports at the top ---
import os, json, re, io, textwrap
from typing import Any, Dict, List, Optional, Iterable
from fastapi import APIRouter, HTTPException, Query, Body, Request
from fastapi.responses import Response
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors

from .rag_routes import _handle_rag_ask

router = APIRouter(prefix="/api/rag", tags=["coding"])
# --------------- JSON Coercion & Parsing ---------------

_CODE_KEYS = ("system","code","title","why","evidence_titles")
_LAB_KEYS  = ("system","code","title","purpose","evidence_titles")
_MED_KEYS  = ("system","code","title","indication","evidence_titles")

def _strip_code_fences(s: Optional[str]) -> str:
    if not s:
        return ""
    s = s.strip()
    if s.startswith("```"):
        # remove leading ```json / ``` and trailing ```
        s = re.sub(r"^```(?:json|JSON)?\s*", "", s)
        s = re.sub(r"\s*```$", "", s)
    return s.strip()

def _parse_model_json(text: Optional[str]) -> Dict[str, Any]:
    if not text:
        return {"_parse_error": "empty ai_response", "_raw": ""}
    raw = _strip_code_fences(text)
    try:
        return json.loads(raw)
    except Exception as e:
        return {"_parse_error": f"{e}", "_raw": text}

def _ensure_list(x: Any) -> List[Any]:
    if x is None: return []
    if isinstance(x, list): return x
    return [x]

def _norm_item(it: Any, kind: str) -> Dict[str, Any]:
    # Turn strings / weird items into structured dicts
    if isinstance(it, dict):
        d = dict(it)
    else:
        # a bare string => treat as title
        d = {"title": str(it)}

    if kind == "code":
        for k in _CODE_KEYS:
            d.setdefault(k, "" if k != "evidence_titles" else [])
    elif kind == "lab":
        for k in _LAB_KEYS:
            d.setdefault(k, "" if k != "evidence_titles" else [])
    elif kind == "med":
        for k in _MED_KEYS:
            d.setdefault(k, "" if k != "evidence_titles" else [])
    else:
        d.setdefault("title", d.get("title",""))
        d.setdefault("evidence_titles", [])

    # normalize evidence_titles to a list[str]
    ev = d.get("evidence_titles", [])
    if isinstance(ev, str):
        ev = [ev]
    elif not isinstance(ev, list):
        ev = []
    d["evidence_titles"] = [str(t).strip() for t in ev if str(t).strip()]
    return d

def _coerce_blocks(J: Dict[str, Any]) -> Dict[str, Any]:
    # Always produce arrays of dicts for these fields
    for key, kind in (
        ("probable_dx","code"),
        ("differential_dx","code"),
        ("procedures","code"),
        ("labs","lab"),
        ("medications","med"),
    ):
        J[key] = [_norm_item(it, kind) for it in _ensure_list(J.get(key, []))]
    return J

# --------------- Citation Matching ---------------

def _match_citation(item: Dict[str, Any], matches: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """
    1) If evidence_titles present, exact title match (case-insensitive).
    2) Else, if system+code present, find a RAG doc whose (source, source_id) looks like it.
    3) Else, fall back to first doc whose title contains the item.title token.
    """
    titles = {t.lower() for t in item.get("evidence_titles", [])}
    title = (item.get("title") or "").lower()
    code  = (item.get("code") or "").strip()
    system= (item.get("system") or "").lower()

    # (1) title match
    for m in matches:
        if titles and (m.get("title") or "").lower() in titles:
            return m

    # (2) source+code-ish match if we have a code
    if code:
        for m in matches:
            src  = (m.get("source") or "").lower()
            sid  = (m.get("source_id") or "")
            if (system.startswith("icd-10") and src.startswith("icd10")) or \
               (system.startswith("icd-11") and src.startswith("icd11")) or \
               (system == "loinc" and src == "loinc") or \
               (system == "rxnorm" and src == "rxnorm"):
                if sid and code and sid.strip().upper() == code.strip().upper():
                    return m

    # (3) fuzzy title contains
    if title:
        for m in matches:
            mt = (m.get("title") or "").lower()
            if title and title in mt:
                return m

    return matches[0] if matches else None

def _excerpt(text: str, needle: str, limit: int = 360) -> str:
    if not text: return ""
    text = re.sub(r"\\s+", " ", text).strip()
    if not needle:
        return text[:limit]
    i = text.lower().find(needle.lower())
    if i < 0:
        return text[:limit]
    start = max(0, i - 120)
    end   = min(len(text), i + 120)
    return text[start:end][:limit]

# --------------- CSV / PDF Builders ---------------

def _rows_for_csv(payload: Dict[str, Any]) -> List[Dict[str, str]]:
    rows = []
    matches = payload.get("matches") or []

    def add(kind: str, arr: List[Dict[str, Any]], why_field: str):
        arr = arr or []
        for it in arr:
            cite = _match_citation(it, matches)
            rows.append({
                "kind": kind,
                "system": it.get("system",""),
                "code": it.get("code",""),
                "title": it.get("title",""),
                "why_or_indication": it.get(why_field,""),
                "citation.source": (cite or {}).get("source",""),
                "citation.doc_key": ((cite or {}).get("meta") or {}).get("doc_key") or (cite or {}).get("source_id",""),
                "citation.title": (cite or {}).get("title",""),
                "excerpt": _excerpt((cite or {}).get("text",""), it.get("title","")),
            })

    add("probable_dx",     payload.get("probable_dx"),     "why")
    add("differential_dx", payload.get("differential_dx"), "why")
    add("procedures",      payload.get("procedures"),      "why")
    add("labs",            payload.get("labs"),            "purpose")
    add("medications",     payload.get("medications"),     "indication")
    return rows

def _csv_bytes(payload: Dict[str, Any]) -> bytes:
    import csv
    buf = io.StringIO()
    fieldnames = ["kind","system","code","title","why_or_indication",
                  "citation.source","citation.doc_key","citation.title","excerpt"]
    w = csv.DictWriter(buf, fieldnames=fieldnames)
    w.writeheader()
    for r in _rows_for_csv(payload):
        w.writerow(r)
    return buf.getvalue().encode("utf-8")

def _pdf_bytes(payload: Dict[str, Any]) -> bytes:
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=LETTER, title="RAG Coding Report")
    styles = getSampleStyleSheet()
    story: List[Any] = []

    def H(txt): story.append(Paragraph(f"<b>{txt}</b>", styles["Heading2"]))
    def P(txt): story.append(Paragraph(textwrap.fill(txt, width=110), styles["BodyText"]))
    def SP(h=8): story.append(Spacer(1, h))

    # Header
    story.append(Paragraph("RAG Coding Report", styles["Title"]))
    SP(4)

    # Clinical Insight
    J = payload.get("insight") or {}
    if isinstance(J, dict) and J.get("assessment"):
        H("Clinical Insight")
        P(J["assessment"]); SP()

    # Compact tables
    def table_for(title, arr, cols, why_label):
        arr = arr or []
        if not arr: return
        H(title); SP(2)
        data = [cols]
        for it in arr:
            row = [str(it.get(c,"")) for c in cols]
            data.append(row)
        tbl = Table(data, repeatRows=1)
        tbl.setStyle(TableStyle([
            ("BACKGROUND",(0,0),(-1,0), colors.lightgrey),
            ("GRID",(0,0),(-1,-1), 0.25, colors.grey),
            ("FONTNAME",(0,0),(-1,0), "Helvetica-Bold"),
        ]))
        story.append(tbl); SP()

    table_for("Probable Diagnoses",     payload.get("probable_dx"),     ["system","code","title","why"], "why")
    table_for("Differential Diagnoses", payload.get("differential_dx"), ["system","code","title","why"], "why")
    table_for("Procedures",             payload.get("procedures"),      ["system","code","title","why"], "why")
    table_for("Labs",                   payload.get("labs"),            ["system","code","title","purpose"], "purpose")
    table_for("Medications",            payload.get("medications"),     ["system","code","title","indication"], "indication")

    # Written Justifications
    matches = payload.get("matches") or []
    H("Code-by-Code Justifications"); SP(2)
    for bucket_key, label, why_key in (
        ("probable_dx","Probable", "why"),
        ("differential_dx","Differential", "why"),
        ("procedures","Procedure", "why"),
        ("labs","Lab", "purpose"),
        ("medications","Medication", "indication"),
    ):
        items = payload.get(bucket_key) or []
        for it in items:
            code_str = " · ".join([x for x in [it.get("system"), it.get("code"), it.get("title")] if x])
            P(f"<b>{label}:</b> {code_str}")
            why = it.get(why_key,"")
            if why: P(f"Why: {why}")
            cite = _match_citation(it, matches)
            if cite:
                src = cite.get("source","")
                title = cite.get("title","")
                dk = ((cite.get("meta") or {}).get("doc_key")) or cite.get("source_id","")
                P(f"Citation: {src} :: {dk} — {title}")
                P("Excerpt: " + _excerpt(cite.get("text",""), it.get("title","")))
            SP(6)

    # Append the source clinical note at the end
    note = (payload.get("note") or "").strip()
    if note:
        H("Source Clinical Note")
        P(note)
        SP(6)

    doc.build(story)
    return buf.getvalue()

# --------------- Main handler ---------------

@router.post("/coding")
async def coding(request: Request, payload: Dict[str, Any] = Body(...),
                 format: str = Query("json", regex="^(json|csv|pdf)$"),
                 pretty: int = Query(0)):
    """
    Body: { note, sources?, limit? }
    """
    note = (payload.get("note") or "").strip()
    sources = payload.get("sources")
    limit = int(payload.get("limit") or 60)

    # Build strict prompting and force JSON output
    from openai import OpenAI
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    model_used = os.getenv("CHAT_MODEL", "gpt-4o-mini")

    PROMPT = f"""
You are a clinical assistant. Return STRICT JSON ONLY (no code fences). Schema:
{{
  "insight": {{
    "assessment": "2-4 sentences",
    "risk_factors": ["..."],
    "red_flags": ["..."],
    "lifestyle_plan": ["..."],
    "follow_up": ["..."]
  }},
  "probable_dx": [{{"system":"ICD-10-CM","code":"","title":"","why":"","evidence_titles":["..."]}}],
  "differential_dx": [{{"system":"ICD-10-CM","code":"","title":"","why":"","evidence_titles":["..."]}}],
  "procedures": [{{"system":"ICD-10-PCS","code":"","title":"","why":"","evidence_titles":["..."]}}],
  "labs": [{{"system":"LOINC","code":"","title":"","purpose":"","evidence_titles":["..."]}}],
  "medications": [{{"system":"RxNorm","code":"","title":"","indication":"","evidence_titles":["..."]}}],
  "patient_education": [{{"topic":"constipation|fiber|gluten|post-appendectomy","evidence_titles":["..."]}}],
  "notes": "brief audit note"
}}
Rules:
- Only include codes/labs/meds if their specific doc was retrieved; otherwise omit.
- Prefer ICD-10-CM/ICD-10-PCS, add ICD-11 if retrieved.
- NO MARKDOWN. JSON object only.
Clinical note:
{note}
""".strip()

    # 1) RAG first
    rag = await _handle_rag_ask(q=note, k=limit, sources_csv=sources, debug=0)
    matches = rag.get("matches") or []

    # 2) Model synthesis with forced JSON
    try:
        resp = client.chat.completions.create(
            model=model_used,
            response_format={"type": "json_object"},
            temperature=0.1,
            messages=[
                {"role":"system","content":"You are a careful clinical assistant. Output must be a single JSON object."},
                {"role":"user", "content":PROMPT + "\n\nUse the retrieved evidence strictly."},
                {"role":"user", "content":"Evidence snippets:\n" + "\n\n".join(
                    f"[{i+1}] {(it.get('source') or 'unknown')} — {(it.get('title') or 'Untitled')}\n{(it.get('text') or '')[:800]}..."
                    for i, it in enumerate(matches[:6])
                )}
            ],
        )
        model_text = (resp.choices[0].message.content or "").strip()
    except Exception:
        model_text = ""

    J = _parse_model_json(model_text)
    J = _coerce_blocks(J)

    # Attach matches for downstream CSV/PDF builders
    payload_out = {
        **J,
        "matches": matches,
        "ai_model": model_used,
        "note": note,  # <-- add note for PDF appending
    }

    if format == "csv":
        return Response(content=_csv_bytes(payload_out), media_type="text/csv",
                        headers={"Content-Disposition":"attachment; filename=coding.csv"})
    if format == "pdf":
        return Response(content=_pdf_bytes(payload_out), media_type="application/pdf",
                        headers={"Content-Disposition":"attachment; filename=coding.pdf"})

    # pretty JSON (no JSONResponse(indent=…))
    body = json.dumps(payload_out, indent=(2 if pretty else None))
    return Response(content=body, media_type="application/json")
