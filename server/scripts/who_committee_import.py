#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Parse WHO Expert Committee Executive Summary PDF into sections and load into Postgres.

Usage:
  python server/scripts/who_committee_import.py \
    --pdf data/who/expert_committee_2025_execsum.pdf \
    --year 2025 --eml 24 --emlc 10 \
    --title "The selection and use of essential medicines, 2025: report of the 25th WHO Expert Committee"

Env: SYNC_DATABASE_URL or DATABASE_URL
Requires: pypdf, psycopg2-binary
"""
import argparse, os, re
import psycopg2
from datetime import date
from pypdf import PdfReader

HEADING_RE = re.compile(r"^(?:[A-Z][A-Z\s\-]{3,}|\d+\.\d+\.?\s+.+)$")

def get_dsn():
    dsn = os.environ.get("SYNC_DATABASE_URL") or os.environ.get("DATABASE_URL")
    if not dsn:
        raise RuntimeError("Set SYNC_DATABASE_URL or DATABASE_URL")
    return dsn.replace("+asyncpg", "")

def pdf_to_sections(pdf_path: str):
    reader = PdfReader(pdf_path)
    pages = [p.extract_text() or "" for p in reader.pages]
    sections = []
    current = {"heading": "EXECUTIVE SUMMARY", "start": 1, "text": []}
    for i, txt in enumerate(pages, start=1):
        lines = [l.strip() for l in (txt.splitlines() if txt else []) if l.strip()]
        if lines and HEADING_RE.match(lines[0]) and i != 1:
            if current["text"]:
                sections.append({
                    "heading": current["heading"],
                    "page_start": current["start"],
                    "page_end": i-1,
                    "text": "\n".join(current["text"]).strip()
                })
            current = {"heading": lines[0][:200], "start": i, "text": []}
        current["text"].append(txt or "")
    if current["text"]:
        sections.append({
            "heading": current["heading"],
            "page_start": current["start"],
            "page_end": len(pages),
            "text": "\n".join(current["text"]).strip()
        })
    return sections

def upsert_report(cur, title, year, eml, emlc, pdf_path):
    cur.execute(
        """
        INSERT INTO guidelines.who_committee_reports(title, year, edition_eml, edition_emlc, file_path, published_on)
        VALUES (%s,%s,%s,%s,%s,%s)
        ON CONFLICT DO NOTHING
        RETURNING report_id
        """,
        (title, year, eml, emlc, pdf_path, date(year, 9, 5))
    )
    row = cur.fetchone()
    if row:
        return row[0]
    cur.execute("SELECT report_id FROM guidelines.who_committee_reports WHERE title=%s AND year=%s", (title, year))
    return cur.fetchone()[0]

def upsert_sections(cur, report_id, sections):
    for s in sections:
        cur.execute(
            """INSERT INTO guidelines.who_committee_sections(report_id, heading, page_start, page_end, text)
               VALUES (%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING""",
            (report_id, s["heading"], s["page_start"], s["page_end"], s["text"])
        )

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pdf", required=True)
    ap.add_argument("--year", type=int, required=True)
    ap.add_argument("--eml", type=int, required=True)
    ap.add_argument("--emlc", type=int, required=True)
    ap.add_argument("--title", required=True)
    args = ap.parse_args()

    sections = pdf_to_sections(args.pdf)
    with psycopg2.connect(get_dsn()) as conn:
        with conn.cursor() as cur:
            report_id = upsert_report(cur, args.title, args.year, args.eml, args.emlc, args.pdf)
            upsert_sections(cur, report_id, sections)
    print(f"Loaded report {args.title} with {len(sections)} sections")

if __name__ == "__main__":
    main()

