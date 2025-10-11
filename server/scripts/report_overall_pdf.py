#!/usr/bin/env python3
import argparse
from report_common import q, connect, build_doc, TableFromRows, P, H2
from reportlab.lib.units import inch

def flow(story, content_width):
    conn = connect()

    story.append(P("RAG Embeddings Coverage (by source)", H2))
    emb = q(conn, """
      SELECT source, COUNT(*) AS n, COUNT(*) FILTER (WHERE embedding IS NULL) AS no_emb
      FROM public.rag_corpus
      GROUP BY 1 ORDER BY n DESC;
    """)
    story.append(TableFromRows(emb, ["source","n","no_emb"], widths=[2.2*inch, 1.0*inch, 1.0*inch]))

    story.append(P("ANN Indexes Present", H2))
    ann = q(conn, """
      SELECT indexname
      FROM pg_indexes
      WHERE tablename='rag_corpus' AND indexname LIKE 'rag_corpus_embedding_ann_%'
      ORDER BY 1;
    """)
    story.append(TableFromRows(ann, ["indexname"], widths=[5.0*inch]))

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--ai", action="store_true", help="include AI analysis")
    args = ap.parse_args()

    ai_obj = None
    if args.ai:
        conn = connect()
        emb = q(conn, """
          SELECT source, COUNT(*) AS n, COUNT(*) FILTER (WHERE embedding IS NULL) AS no_emb
          FROM public.rag_corpus GROUP BY 1 ORDER BY n DESC;
        """)
        from report_common import ai_analyze
        ai_obj = ai_analyze("overall", {"rag_sources": emb})

    build_doc(args.out, "2ndOpinionMD — Overall DB Integrity", None, flow, ai_obj=ai_obj)

if __name__ == "__main__":
    main()
