import json, os, sys
import psycopg2
import psycopg2.extras as pe
from dotenv import dotenv_values

cfg = dotenv_values(os.path.join("server",".env"))
DATABASE_URL = cfg.get("DATABASE_URL") or os.getenv("DATABASE_URL")
SRC = os.path.join("server","data","medical_data.json")

def rows():
    with open(SRC, "r", encoding="utf-8") as f:
        data = json.load(f)
        if isinstance(data, dict) and "caseStudies" in data:
            for case in data["caseStudies"]:
                yield case
        elif isinstance(data, list):
            for d in data:
                yield d
        else:
            yield data

def pick(d):
    title = d.get("title") or d.get("name") or d.get("primaryCondition") or d.get("caseId") or None
    body  = d.get("body") or d.get("text") or d.get("description") or d.get("content") or d.get("summary") or None
    
    if not body and "symptomTimeline" in d:
        parts = []
        if d.get("primaryCondition"):
            parts.append(f"Primary Condition: {d['primaryCondition']}")
        if d.get("symptomTimeline"):
            parts.append(f"Symptoms: {'; '.join(d['symptomTimeline']) if isinstance(d['symptomTimeline'], list) else d['symptomTimeline']}")
        if d.get("diagnosticZone"):
            parts.append(f"Diagnostic Zone: {d['diagnosticZone']}")
        if d.get("staxScore"):
            parts.append(f"STAX Score: {d['staxScore']}")
        body = ". ".join(parts)
    
    meta = {k:v for k,v in d.items() if k not in ("title","name","primaryCondition","caseId","body","text","description","content","summary","symptomTimeline")}
    return (title, body, json.dumps(meta, ensure_ascii=False))

def main():
    if not DATABASE_URL: raise SystemExit("Set DATABASE_URL")
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()
    batch = [pick(d) for d in rows()]
    if not batch:
        print("No docs found in medical_data.json")
        return
    pe.execute_values(cur, """
      INSERT INTO public.medical_knowledge (title, body, metadata)
      VALUES %s ON CONFLICT DO NOTHING
    """, batch, page_size=1000)
    conn.commit(); conn.close()
    print(f"Inserted {len(batch)} docs")

if __name__ == "__main__":
    main()
