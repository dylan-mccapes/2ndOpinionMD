#!/usr/bin/env python3
"""
Build unified RAG corpus from multiple sources:
- medical_knowledge (primary)
- HPO terms (concise definitions)
- Orphanet diseases (brief summaries)
- SNOMED concepts (FSN only)
"""

import os
import sys
import psycopg2
import psycopg2.extras as pe
from dotenv import load_dotenv

def main():
    load_dotenv()
    
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("ERROR: DATABASE_URL not found in environment", file=sys.stderr)
        sys.exit(1)
    
    import urllib.parse
    parsed = urllib.parse.urlparse(database_url)
    
    conn = psycopg2.connect(
        host=parsed.hostname,
        port=parsed.port,
        user=parsed.username,
        password=parsed.password,
        database=parsed.path[1:]  # Remove leading slash
    )
    
    cur = conn.cursor()
    
    print("🏗️ Creating unified RAG corpus table...")
    
    cur.execute("""
        CREATE TABLE IF NOT EXISTS public.rag_corpus (
          id        bigserial PRIMARY KEY,
          source    text NOT NULL,
          source_id text,
          title     text,
          text      text NOT NULL,
          metadata  jsonb DEFAULT '{}'::jsonb,
          embedding vector,
          ts        tsvector
        )
    """)
    
    print("📚 Seeding from medical_knowledge (primary)...")
    
    cur.execute("""
        INSERT INTO public.rag_corpus (source, source_id, title, text, metadata)
        SELECT 'medical_knowledge', mk.id::text, mk.title, 
               COALESCE(mk.body, mk.title), mk.metadata
        FROM public.medical_knowledge mk
        ON CONFLICT DO NOTHING
    """)
    
    medical_count = cur.rowcount
    print(f"  ✅ Added {medical_count} medical_knowledge entries")
    
    print("🧬 Adding HPO terms (concise definitions)...")
    
    try:
        conn.commit()  # Commit previous work first
        cur.execute("""
            INSERT INTO public.rag_corpus (source, source_id, title, text, metadata)
            SELECT 'hpo', h.hpo_id, h.name, h.definition,
                   jsonb_build_object('hpo_id', h.hpo_id)
            FROM ontology.hpo_terms h
            WHERE h.definition IS NOT NULL 
              AND length(h.definition) BETWEEN 50 AND 600
            ON CONFLICT DO NOTHING
        """)
        hpo_count = cur.rowcount
        print(f"  ✅ Added {hpo_count} HPO term entries")
        conn.commit()
    except psycopg2.Error as e:
        print(f"  ⚠️ HPO terms table not accessible: {e}")
        conn.rollback()
        hpo_count = 0
    
    print("🦋 Adding Orphanet diseases (brief summaries)...")
    
    try:
        cur.execute("""
            INSERT INTO public.rag_corpus (source, source_id, title, text, metadata)
            SELECT 'orphanet', d.orpha_code::text, d.preferred_term,
                   COALESCE(d.definition, d.preferred_term),
                   jsonb_build_object('orpha_code', d.orpha_code)
            FROM ontology.orphanet_diseases d
            WHERE COALESCE(d.definition,'') <> ''
              AND length(d.definition) BETWEEN 80 AND 800
            ON CONFLICT DO NOTHING
        """)
        orphanet_count = cur.rowcount
        print(f"  ✅ Added {orphanet_count} Orphanet disease entries")
        conn.commit()
    except psycopg2.Error as e:
        print(f"  ⚠️ Orphanet diseases table not accessible: {e}")
        conn.rollback()
        orphanet_count = 0
    
    print("🏥 Adding SNOMED concepts (FSN only)...")
    
    try:
        cur.execute("""
            INSERT INTO public.rag_corpus (source, source_id, title, text, metadata)
            SELECT 'snomed', c.conceptid::text, d.term, d.term,
                   jsonb_build_object('conceptId', c.conceptid)
            FROM ontology.concepts c
            JOIN ontology.descriptions d ON d.conceptid = c.conceptid
            WHERE d.active = 1 AND d.typeid IN ('900000000000003001')
            LIMIT 100000
        """)
        snomed_count = cur.rowcount
        print(f"  ✅ Added {snomed_count} SNOMED concept entries")
        conn.commit()
    except psycopg2.Error as e:
        print(f"  ⚠️ SNOMED concepts table not accessible: {e}")
        conn.rollback()
        snomed_count = 0
    
    print("📝 Creating full-text search vectors...")
    
    cur.execute("""
        UPDATE public.rag_corpus
        SET ts = to_tsvector('english', COALESCE(title,'') || ' ' || COALESCE(text,''))
        WHERE ts IS NULL OR ts = ''::tsvector
    """)
    
    print("🔍 Creating indexes...")
    
    cur.execute("""
        CREATE INDEX IF NOT EXISTS rag_corpus_ts_idx
          ON public.rag_corpus USING GIN (ts)
    """)
    
    cur.execute("""
        CREATE INDEX IF NOT EXISTS rag_corpus_source_idx
          ON public.rag_corpus (source)
    """)
    
    conn.commit()
    
    cur.execute("SELECT COUNT(*) FROM public.rag_corpus")
    total_count = cur.fetchone()[0]
    
    print(f"\n🎉 RAG corpus built successfully!")
    print(f"  📊 Total entries: {total_count}")
    print(f"  📚 Medical knowledge: {medical_count}")
    print(f"  🧬 HPO terms: {hpo_count}")
    print(f"  🦋 Orphanet diseases: {orphanet_count}")
    print(f"  🏥 SNOMED concepts: {snomed_count}")
    
    cur.close()
    conn.close()

if __name__ == "__main__":
    main()
