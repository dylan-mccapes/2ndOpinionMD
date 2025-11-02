-- 15_disgenet_audit.sql  (save anywhere / run in psql)
WITH base AS (
  SELECT *
  FROM   molecular.disgenet_associations
),
tot AS (
  SELECT
    COUNT(*)                                AS rows,
    COUNT(DISTINCT assoc_id)                AS assoc_ids,
    COUNT(*) FILTER (WHERE assoc_id IS NULL) AS null_assoc_ids,
    COUNT(DISTINCT gene_symbol)             AS genes,
    COUNT(DISTINCT gene_ncbi_id)            AS gene_ids,
    COUNT(DISTINCT disease_name)            AS diseases
  FROM base
),
nulls AS (
  SELECT
    COUNT(*) FILTER (WHERE gene_symbol   IS NULL) AS null_gene_symbol,
    COUNT(*) FILTER (WHERE gene_ncbi_id  IS NULL) AS null_gene_id,
    COUNT(*) FILTER (WHERE disease_name  IS NULL) AS null_disease_name,
    COUNT(*) FILTER (WHERE score         IS NULL) AS null_score
  FROM base
),
dupes AS (
  SELECT COUNT(*) AS assoc_dupes
  FROM (
    SELECT assoc_id
    FROM base
    WHERE assoc_id IS NOT NULL
    GROUP BY assoc_id
    HAVING COUNT(*) > 1
  ) d
),
score_hist AS (
  SELECT
    width_bucket(score, 0.0, 1.0, 10) AS bucket,
    COUNT(*)                          AS n
  FROM base
  WHERE score IS NOT NULL
  GROUP BY 1
),
per_gene AS (
  SELECT gene_symbol, COUNT(*) AS n
  FROM base
  GROUP BY 1
  ORDER BY n DESC NULLS LAST
  LIMIT 20
),
per_disease AS (
  SELECT disease_name, COUNT(*) AS n
  FROM base
  GROUP BY 1
  ORDER BY n DESC NULLS LAST
  LIMIT 20
),
top_hits AS (
  SELECT gene_symbol, disease_name, score, num_pmids
  FROM base
  ORDER BY score DESC NULLS LAST, num_pmids DESC NULLS LAST
  LIMIT 20
)
SELECT json_build_object(
  'totals',        (SELECT row_to_json(tot)      FROM tot),
  'nulls',         (SELECT row_to_json(nulls)    FROM nulls),
  'duplicates',    (SELECT row_to_json(dupes)    FROM dupes),
  'score_hist',    (SELECT json_agg(row_to_json(score_hist) ORDER BY bucket) FROM score_hist),
  'top_genes',     (SELECT json_agg(row_to_json(per_gene))   FROM per_gene),
  'top_diseases',  (SELECT json_agg(row_to_json(per_disease))FROM per_disease),
  'top_hits',      (SELECT json_agg(row_to_json(top_hits))   FROM top_hits)
) AS disgenet_audit;

-- database/sql/15_disgenet_audit.sql
WITH
totals AS (
  SELECT
    COUNT(*)::int                              AS rows,
    COUNT(DISTINCT assoc_id)::int              AS assoc_ids,
    COUNT(*) FILTER (WHERE assoc_id IS NULL)   AS null_assoc_ids,
    COUNT(DISTINCT gene_symbol)::int           AS genes,
    COUNT(DISTINCT gene_ncbi_id)::int          AS gene_ids,
    COUNT(DISTINCT disease_name)::int          AS diseases
  FROM molecular.disgenet_associations
),
nulls AS (
  SELECT
    COUNT(*) FILTER (WHERE gene_symbol    IS NULL)::int AS null_gene_symbol,
    COUNT(*) FILTER (WHERE gene_ncbi_id   IS NULL)::int AS null_gene_id,
    COUNT(*) FILTER (WHERE disease_name   IS NULL)::int AS null_disease_name,
    COUNT(*) FILTER (WHERE score          IS NULL)::int AS null_score
  FROM molecular.disgenet_associations
),
duplicates AS (
  SELECT COUNT(*)::int AS assoc_dupes
  FROM (
    SELECT assoc_id
    FROM molecular.disgenet_associations
    WHERE assoc_id IS NOT NULL
    GROUP BY assoc_id
    HAVING COUNT(*) > 1
  ) d
),
score_hist AS (
  SELECT
    w AS bucket,
    COUNT(*)::int AS n
  FROM (
    SELECT GREATEST(0, LEAST(10, width_bucket(COALESCE(score, 0), 0, 1, 10))) AS w
    FROM molecular.disgenet_associations
  ) x
  GROUP BY 1
  ORDER BY 1
),
top_genes AS (
  SELECT gene_symbol, COUNT(*)::int AS n
  FROM molecular.disgenet_associations
  WHERE gene_symbol IS NOT NULL
  GROUP BY 1 ORDER BY 2 DESC, 1 ASC LIMIT 20
),
top_diseases AS (
  SELECT disease_name, COUNT(*)::int AS n
  FROM molecular.disgenet_associations
  WHERE disease_name IS NOT NULL
  GROUP BY 1 ORDER BY 2 DESC, 1 ASC LIMIT 20
),
top_hits AS (
  SELECT gene_symbol, disease_name,
         score::float AS score,
         num_pmids::int AS num_pmids
  FROM molecular.disgenet_associations
  ORDER BY score DESC NULLS LAST, num_pmids DESC NULLS LAST
  LIMIT 20
),
ai AS (
  SELECT
    CASE
      WHEN t.rows = 0 THEN 'FAIL'
      WHEN d.assoc_dupes > 0 THEN 'FAIL'
      WHEN (n.null_gene_symbol + n.null_gene_id + n.null_disease_name) > 0 THEN 'WARN'
      WHEN t.genes < 100 THEN 'WARN'
      ELSE 'PASS'
    END AS status,
    ARRAY_REMOVE(ARRAY[
      CASE WHEN t.rows = 0 THEN 'Table exists but contains no rows' END,
      CASE WHEN d.assoc_dupes > 0 THEN d.assoc_dupes || ' duplicate assoc_id value(s)' END,
      CASE WHEN (n.null_gene_symbol + n.null_gene_id + n.null_disease_name) > 0
           THEN 'NULLs present in required fields (gene_symbol/gene_id/disease_name)' END,
      CASE WHEN t.genes < 100 THEN 'Low gene coverage for demo slice (' || t.genes || ' genes)' END
    ], NULL) AS reasons
  FROM totals t, nulls n, duplicates d
)
SELECT json_build_object(
  'totals',       (SELECT row_to_json(t) FROM totals t),
  'nulls',        (SELECT row_to_json(n) FROM nulls n),
  'duplicates',   (SELECT row_to_json(d) FROM duplicates d),
  'score_hist',   (SELECT json_agg(s) FROM score_hist s),
  'top_genes',    (SELECT json_agg(g) FROM top_genes g),
  'top_diseases', (SELECT json_agg(dd) FROM top_diseases dd),
  'top_hits',     (SELECT json_agg(h) FROM top_hits h),
  'ai',           (SELECT row_to_json(a) FROM ai a)
);
