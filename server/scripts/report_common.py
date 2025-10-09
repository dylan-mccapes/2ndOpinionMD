#!/usr/bin/env python3
"""
Common helpers for DB integrity PDF reports.

Exports:
  - connect()
  - q(conn, sql, params=None)
  - build_doc(out_path, title, subtitle, build_flow, ai_obj=None)
  - TableFromRows(rows, columns, widths=None)
  - P (Paragraph alias)
  - H1, H2, H3, BODY (styles)
"""

import os
import datetime as dt
from typing import Any, Dict, Iterable, List, Optional, Sequence

import psycopg2
import psycopg2.extras

from reportlab.lib import colors
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)

# ---------- Styles (stable alias) ----------
_STYLES = getSampleStyleSheet()
# Public alias for back-compat (some modules import STYLES directly)
STYLES = _STYLES

H1 = STYLES['Heading1']
H2 = STYLES['Heading2']
H3 = STYLES['Heading3']
BODY = STYLES['BodyText']

# A paragraph style that wraps long text robustly (even long "words"/JSON)
WRAP_STYLE = ParagraphStyle(
    'wrap',
    parent=BODY,
    wordWrap='CJK',
    splitLongWords=True,
    leading=13,
)
SMALL = ParagraphStyle('small', parent=BODY, fontSize=8, leading=10)

# Convenience alias so callers can do: from report_common import P
P = Paragraph


# ---------- Database helpers ----------

def connect():
    """
    Connect to Postgres using SYNC_DATABASE_URL or a local default.
    """
    dsn = os.environ.get(
        "SYNC_DATABASE_URL",
        "postgresql://2ndopinionmd@localhost:5432/2ndopinionmd",
    )
    return psycopg2.connect(dsn)


def q(conn, sql: str, params=None):
    """
    Run a query and return list[dict]. IMPORTANT: never pass an empty tuple/dict
    for params when there are no placeholders; pass None so psycopg2 won't
    try to apply Python % formatting to bare % in SQL string literals.
    """
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(sql, params if params is not None else None)
        return list(cur.fetchall())

# ---------- Formatting helpers ----------

def fmt_bytes(n: Optional[int]) -> str:
    """
    Human-friendly byte size.
    """
    if n is None:
        return ""
    try:
        n = int(n)
    except Exception:
        return str(n)
    units = ['B', 'KB', 'MB', 'GB', 'TB']
    i = 0
    f = float(n)
    while f >= 1024 and i < len(units) - 1:
        f /= 1024.0
        i += 1
    return f"{f:.1f}{units[i]}"


def _to_para(value: Any, style: ParagraphStyle = WRAP_STYLE) -> Paragraph:
    """
    Safely wrap any value into a Paragraph with wrapping.
    """
    from xml.sax.saxutils import escape
    if value is None:
        s = ""
    elif isinstance(value, (int, float)):
        # Numbers: show as plain text (no thousands sep to keep width compact)
        s = str(value)
    else:
        s = str(value)
    return Paragraph(escape(s), style)


def TableFromRows(
    rows: Iterable[Dict[str, Any]] | Iterable[Sequence[Any]],
    columns: Sequence[str],
    widths: Optional[Sequence[float]] = None,
) -> Table:
    """
    Build a wrapped, styled table from rows (list of dicts or tuples)
    using explicit column order.
    - Auto-formats columns ending with '_bytes' or exactly 'size_bytes'.
    - Right-aligns numeric columns.
    """
    # Normalize rows -> list[dict]
    norm: List[Dict[str, Any]] = []
    for r in rows:
        if isinstance(r, dict):
            norm.append(r)
        else:
            # Treat as sequence; map by index into columns
            norm.append({columns[i]: r[i] if i < len(r) else None for i in range(len(columns))})

    # Header row
    data: List[List[Any]] = [[Paragraph(f"<b>{c}</b>", BODY) for c in columns]]

    # Body rows with formatting
    for r in norm:
        row: List[Any] = []
        for c in columns:
            v = r.get(c, None)
            if c == 'size_bytes' or c.endswith('_bytes'):
                row.append(_to_para(fmt_bytes(v)))
            else:
                row.append(_to_para(v))
        row = row
        data.append(row)

    t = Table(data, colWidths=list(widths) if widths else None, hAlign='LEFT')
    t.setStyle(TableStyle([
        ('GRID', (0, 0), (-1, -1), 0.25, colors.lightgrey),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('BACKGROUND', (0, 0), (-1, 0), colors.whitesmoke),
    ]))

    # Right-align numeric-looking columns
    num_cols = set()
    for ci, c in enumerate(columns):
        # If any body cell is a number, mark as numeric
        for ri in range(1, len(data)):
            cell_text = norm[ri - 1].get(c, None)
            if isinstance(cell_text, (int, float)):
                num_cols.add(ci)
                break
    for ci in num_cols:
        t.setStyle(TableStyle([('ALIGN', (ci, 1), (ci, -1), 'RIGHT')]))

    return t

# ---------- AI assessment block ----------
def ai_analyze(
    kind: str | None = None,
    facts: dict | None = None,
    *,
    system: str | None = None,
    user: str | dict | None = None,
    model: str | None = None,
) -> dict:
    """
    Flexible AI call for integrity grading.

    Usage (new, explicit prompts):
        ai_analyze(system="You are auditing...", user={"tables":[...], "counts":{...}})

    Usage (legacy, structured):
        ai_analyze(kind="hpo_integrity", facts={"tables":[...], "counts":{...}})

    Returns:
      {"verdict": "pass"|"warn"|"fail"|"info", "rationale": "<brief text>"}

    - Never raises; on error returns {"verdict":"info","rationale":"..."}.
    - `model` overrides REPORTS_AI_MODEL env var (defaults to gpt-4o-mini).
    """
    import os, json

    model = model or os.getenv("REPORTS_AI_MODEL", "gpt-4o-mini")

    # Compact + truncate so we don't blow up tokens
    def compact(obj, max_chars=20000) -> str:
        try:
            s = json.dumps(obj, separators=(",", ":"), default=str)
        except Exception:
            s = str(obj)
        return (s[:max_chars] + "...[truncated]") if len(s) > max_chars else s

    default_system = (
        "You are a meticulous database integrity QA assistant. "
        "Given JSON facts about a dataset, reply ONLY with a JSON object:\n"
        '{ "verdict": "pass|warn|fail|info", "rationale": "<=3 concise sentences>" } '
        "where 'verdict' reflects overall integrity risk."
    )

    # Prefer explicit system/user if provided; otherwise build from kind/facts.
    sys_msg = system or default_system
    if user is None:
        payload = {"kind": kind or "generic", "facts": facts or {}}
        user_msg = compact(payload)
    else:
        user_msg = compact(user)

    try:
        try:
            # New SDK
            from openai import OpenAI
            client = OpenAI()
            resp = client.chat.completions.create(
                model=model,
                temperature=0,
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": sys_msg},
                    {"role": "user", "content": user_msg},
                ],
            )
            txt = resp.choices[0].message.content
        except Exception:
            # Legacy SDK fallback
            import openai as legacy_openai  # type: ignore
            if not os.getenv("OPENAI_API_KEY"):
                raise RuntimeError("OPENAI_API_KEY not set")
            legacy_openai.api_key = os.getenv("OPENAI_API_KEY")
            resp = legacy_openai.ChatCompletion.create(
                model=model,
                temperature=0,
                messages=[
                    {"role": "system", "content": sys_msg + " Respond ONLY with valid JSON."},
                    {"role": "user", "content": user_msg},
                ],
            )
            txt = resp["choices"][0]["message"]["content"]

        data = json.loads(txt)
        verdict = str(data.get("verdict", "info")).strip().lower()
        if verdict not in ("pass", "warn", "fail", "info"):
            verdict = "info"
        rationale = str(data.get("rationale", "")).strip()
        return {"verdict": verdict, "rationale": rationale or "No AI rationale provided."}
    except Exception as e:
        return {
            "verdict": "info",
            "rationale": f"AI analysis unavailable or failed: {type(e).__name__}: {e}",
        }

def render_ai_assessment(story, title: str, ai_obj: dict, content_width: float):
    """
    Render a compact AI assessment block with verdict + wrapped rationale.
    """
    story.append(Spacer(1, 6))
    story.append(P(title, H2))

    ai = ai_obj or {}
    verdict = str(ai.get("verdict", "info")).strip().lower() or "info"
    rationale_text = (ai.get("rationale") or "No AI rationale provided.").strip()

    palette = {
        "pass": colors.HexColor("#1b9e77"),
        "warn": colors.HexColor("#d95f02"),
        "fail": colors.HexColor("#e7298a"),
        "info": colors.HexColor("#2e86de"),
    }
    bg = palette.get(verdict, colors.lightgrey)
    fg = colors.white if bg != colors.lightgrey else colors.black

    gap = 6
    vw = 0.95 * inch
    rw = max(content_width - vw - gap, 2.5 * inch)

    verdict_style = ParagraphStyle('verdict', parent=STYLES['BodyText'], alignment=1, textColor=fg, leading=12)
    verdict_para = P(f"<b>{verdict.upper()}</b>", verdict_style)
    rationale_para = P(rationale_text, WRAP_STYLE)

    tbl = Table([[verdict_para, rationale_para]], colWidths=[vw, rw], hAlign='LEFT')
    tbl.setStyle(TableStyle([
        ('BACKGROUND',   (0, 0), (0, 0), bg),
        ('TEXTCOLOR',    (0, 0), (0, 0), fg),
        ('BOX',          (0, 0), (-1, -1), 0.25, colors.grey),
        ('VALIGN',       (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING',  (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING',   (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING',(0, 0), (-1, -1), 4),
    ]))

    story.append(tbl)
    story.append(Spacer(1, 6))


# ---------- Document builder ----------

def build_doc(
    out_path: str,
    title: str,
    subtitle: Optional[str],
    build_flow,
    ai_obj: Optional[dict] = None,
    pagesize=LETTER,
    left_margin=0.7 * inch,
    right_margin=0.7 * inch,
    top_margin=0.6 * inch,
    bottom_margin=0.6 * inch,
):
    """
    Build a simple one-column PDF.
    - build_flow(story, content_width) should append content to `story`.
    - ai_obj (optional) renders an AI assessment box at the end.
    """
    doc = SimpleDocTemplate(
        out_path,
        pagesize=pagesize,
        leftMargin=left_margin,
        rightMargin=right_margin,
        topMargin=top_margin,
        bottomMargin=bottom_margin,
        title=title,
        author="2ndOpinionMD",
        subject="Database Integrity Report",
    )
    story: List[Any] = []

    # Header
    story.append(P(title, H1))
    if subtitle:
        story.append(Spacer(1, 3))
        story.append(P(subtitle, BODY))
    story.append(Spacer(1, 6))
    story.append(P(f"Generated: {dt.datetime.now(dt.timezone.utc).isoformat()}", SMALL))
    story.append(Spacer(1, 10))

    # Content
    content_width = doc.width  # available width within margins
    build_flow(story, content_width)

    # Optional AI analysis
    if ai_obj:
        render_ai_assessment(story, "AI Integrity Assessment", ai_obj, content_width)

    doc.build(story)
    print(f"Wrote {out_path}")
