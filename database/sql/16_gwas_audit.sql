-- database/sql/16_gwas_audit.sql
WITH b AS (
  SELECT * FROM molecular.gwas_hits
),
t AS (
  SELECT COUNT(*)::int AS rows FROM b
),
nulls AS (
  SELECT
    COUNT(*) FILTER (WHERE disease_trait IS NULL)::int AS null_disease_trait,
    COUNT(*) FILTER (WHERE mapped_trait  IS NULL)::int AS null_mapped_trait,
    COUNT(*) FILTER (WHERE snps          IS NULL)::int AS null_snps,
    COUNT(*) FILTER (WHERE p_value       IS NULL)::int AS null_p_value
  FROM b
),
dupes AS (
  SELECT COUNT(*)::int AS groups, COALESCE(SUM(n-1),0)::int AS rows_over_min
  FROM (
    SELECT
      COALESCE(study_accession,'') AS study,
      COALESCE(snps,'')            AS snps,
      COALESCE(disease_trait,'')   AS trait,
      COUNT(*)::int                AS n
    FROM b
    GROUP BY 1,2,3
    HAVING COUNT(*) > 1
  ) d
),
hist AS (
  -- bucket = floor(max(5, min(300, -log10(p))))
  SELECT
    GREATEST(5, LEAST(300,
      FLOOR( (-LN(p_value)/LN(10))::numeric )
    ))::int AS bucket,
    COUNT(*)::int AS n
  FROM b
  WHERE p_value IS NOT NULL AND p_value > 0
  GROUP BY 1
  ORDER BY 1
),
traits AS (
  SELECT disease_trait, COUNT(*)::int AS n
  FROM b GROUP BY 1
  ORDER BY n DESC NULLS LAST
  LIMIT 25
),
snps AS (
  SELECT snps, COUNT(*)::int AS n
  FROM b WHERE snps IS NOT NULL
  GROUP BY 1
  ORDER BY n DESC
  LIMIT 25
),
best AS (
  SELECT
    disease_trait, mapped_trait, snps, p_value,
    strongest_snp_risk_allele, mapped_gene, reported_genes
  FROM b
  ORDER BY p_value ASC NULLS LAST
  LIMIT 25
)
SELECT json_build_object(
  'presence', json_build_object(
      'has_table', TRUE,
      'rows', (SELECT rows FROM t)
  ),
  'nulls', (SELECT to_jsonb(nulls) FROM nulls),
  'duplicates', (SELECT json_build_object(
      'groups',        COALESCE(groups,0),
      'rows_over_min', COALESCE(rows_over_min,0)
  ) FROM dupes),
  'score_hist', (SELECT COALESCE(
      json_agg(json_build_object('bucket', bucket, 'n', n) ORDER BY bucket),
      '[]'::json
  ) FROM hist),
  'score_hist_total_bins', (SELECT COUNT(*) FROM hist),
  'top_traits', (SELECT COALESCE(
      json_agg(json_build_object('disease_trait', disease_trait, 'n', n)),
      '[]'::json
  ) FROM traits),
  'top_snps', (SELECT COALESCE(
      json_agg(json_build_object('snps', snps, 'n', n)),
      '[]'::json
  ) FROM snps),
  'best_hits', (SELECT COALESCE(
      json_agg(json_build_object(
        'disease_trait',              disease_trait,
        'mapped_trait',               mapped_trait,
        'snps',                       snps,
        'p_value',                    p_value,
        'strongest_snp_risk_allele',  strongest_snp_risk_allele,
        'mapped_gene',                mapped_gene,
        'reported_genes',             reported_genes
      )),
      '[]'::json
  ) FROM best)
) AS audit;
