#!/usr/bin/env python3
"""
Upsert GWAS rows from molecular.gwas_hits into public.rag_corpus (source='gwas'),
and refresh FTS (ts) for any missing rows.

Env:
  SYNC_DATABASE_URL  (preferred)  e.g., postgresql://user@localhost:5432/2ndopinionmd
  DATABASE_URL       (fallback; '+asyncpg' will be stripped)

CLI (optional):
  --since YYYY-MM-DD   Only consider GWAS rows with date_added >= since
  --dry-run            Print counts, do not insert
"""
import os, sys, argparse
from pathlib import Path
import psycopg2

def resolve_dsn() -> str:
    dsn = os.environ.get("SYNC_DATABASE_URL")
    if dsn:
        return dsn
    dsn = os.environ.get("DATABASE_URL")
    if not dsn:
        raise SystemExit("ERROR: set SYNC_DATABASE_URL or DATABASE_URL in env.")
    if dsn.startswith("postgresql+asyncpg://"):
        dsn = "postgresql://" + dsn.split("postgresql+asyncpg://", 1)[1]
    return dsn

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--since", type=str, default=None, help="YYYY-MM-DD filter on gwas.date_added")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    dsn = resolve_dsn()
    where_since = ""
    params = {}
    if args.since:
        where_since = "AND g.date_added >= %(since)s"
        params["since"] = args.since

    # Compose once; computed title provides a natural key
    insert_sql = f"""
    WITH src AS (
      SELECT
        'gwas'::text AS source,
        concat_ws(' ', 'GWAS:', coalesce(g.disease_trait,''), '—', coalesce(g.snps,''), '—', coalesce(g.study_accession,'')) AS title,
        trim(both ' ' from concat_ws(' ',
          'Trait:', coalesce(g.disease_trait,''),
          '| Mapped:', coalesce(g.mapped_trait,''),
          '| SNPs:', coalesce(g.snps,''),
          '| Strongest:', coalesce(g.strongest_snp_risk_allele,''),
          '| p=', coalesce(g.p_value::text,''),
          '| OR/BETA:', coalesce(g.or_beta,''),
          '| Genes(reported):', coalesce(g.reported_genes,''),
          '| Genes(mapped):', coalesce(g.mapped_gene,''),
          '| Study:', coalesce(g.study_accession,''),
          '| PubMed:', coalesce(g.pubmed_id,''),
          '| Chr:', coalesce(g.chr,''), '@', coalesce(g.chr_pos::text,''),
          '| Added:', coalesce(g.date_added::text,'')
        )) AS text,
        to_tsvector('english',
          coalesce(g.disease_trait,'')||' '||
          coalesce(g.mapped_trait,'') ||' '||
          coalesce(g.reported_genes,'')||' '||
          coalesce(g.mapped_gene,'')   ||' '||
          coalesce(g.snps,'')
        ) AS ts
      FROM molecular.gwas_hits g
      WHERE 1=1 {where_since}
    )
    INSERT INTO public.rag_corpus (source, title, text, ts)
    SELECT s.source, s.title, s.text, s.ts
    FROM src s
    WHERE NOT EXISTS (
      SELECT 1 FROM public.rag_corpus rc
      WHERE rc.source = 'gwas' AND rc.title = s.title
    );
    """

    update_ts_sql = """
    UPDATE public.rag_corpus
    SET ts = to_tsvector('english', coalesce(title,'') || ' ' || coalesce(text,''))
    WHERE source = 'gwas' AND ts IS NULL;
    """

    count_sql = """
    SELECT
      (SELECT count(*) FROM molecular.gwas_hits) AS gwas_all,
      (SELECT count(*) FROM molecular.gwas_hits WHERE date_added >= %(since)s) AS gwas_since,
      (SELECT count(*) FROM public.rag_corpus WHERE source='gwas') AS rag_gwas;
    """

    with psycopg2.connect(dsn) as conn, conn.cursor() as cur:
        if args.since:
            cur.execute(count_sql, {"since": args.since})
            g_all, g_since, rag_g = cur.fetchone()
            print(f"[pre] gwas(all)={g_all} gwas(since {args.since})={g_since} rag.gwas={rag_g}")
        else:
            cur.execute("SELECT COUNT(*) FROM molecular.gwas_hits")
            print(f"[pre] gwas(all)={cur.fetchone()[0]}")

        if args.dry_run:
            print("[dry-run] Skipping insert/update.")
            return

        cur.execute(insert_sql, params)
        inserted = cur.rowcount if cur.rowcount is not None else 0
        print(f"Inserted rows: {inserted}")

        cur.execute(update_ts_sql)
        updated = cur.rowcount if cur.rowcount is not None else 0
        print(f"FTS ts backfilled (NULL→ts): {updated}")

        conn.commit()

        cur.execute("SELECT COUNT(*) FROM public.rag_corpus WHERE source='gwas'")
        print(f"[post] rag.gwas={cur.fetchone()[0]}")

if __name__ == "__main__":
    main()

