#!/usr/bin/env python
import os, json, argparse, datetime as dt
from reportlab.lib.pagesizes import LETTER, landscape
from reportlab.pdfgen import canvas

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="inp", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    with open(args.inp) as f:
        d = json.load(f)

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    c = canvas.Canvas(args.out, pagesize=landscape(LETTER))
    w, h = landscape(LETTER)

    y = h - 40
    c.setFont("Helvetica-Bold", 18)
    c.drawString(40, y, "ICD Integrity Report")
    y -= 24
    c.setFont("Helvetica", 10)
    c.drawString(40, y, f"Generated: {dt.datetime.now().isoformat(timespec='seconds')}")
    y -= 20

    def row(label, key):
        nonlocal y
        c.setFont("Helvetica-Bold", 11); c.drawString(40, y, f"{label}:")
        c.setFont("Helvetica", 11);      c.drawRightString(w-40, y, str(d.get(key, "")))
        y -= 16

    c.setFont("Helvetica-Bold", 14); c.drawString(40, y, "ICD-10-CM & RAG"); y -= 20
    row("ICD-10-CM base rows (ontology.icd10cm)", "icd10cm_codes")
    row("icd10cm_targets view rows", "icd10cm_targets")
    row("RAG rows (icd10cm)", "rag_rows")
    row("RAG missing embeddings", "rag_missing")
    row("RAG embedded", "rag_embedded")
    y -= 10

    c.setFont("Helvetica-Bold", 14); c.drawString(40, y, "SNOMED → ICD-10-CM Map"); y -= 20
    row("Total map rows", "map_rows_all")
    row("Rows with target", "map_rows_with_target")
    row("Distinct ICD-10-CM codes", "map_distinct_icd10cm_codes")
    row("Valid codes (plain)", "map_valid_plain")
    row("Valid w/ placeholders (X/? )", "map_valid_with_placeholders")
    row("Truly invalid (empty)", "map_truly_invalid")

    c.showPage()
    c.save()
    print(f"Wrote {args.out}")

if __name__ == "__main__":
    main()
