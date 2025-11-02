CREATE OR REPLACE VIEW molecular.v_clinvar_significance AS
SELECT clinicalsignificance AS significance, COUNT(*)::bigint AS n
FROM molecular.clinvar_summary
GROUP BY 1
ORDER BY n DESC NULLS LAST;

CREATE OR REPLACE VIEW molecular.v_clinvar_by_gene AS
SELECT genesymbol AS gene, COUNT(*)::bigint AS n
FROM molecular.clinvar_summary
WHERE genesymbol IS NOT NULL AND genesymbol <> '-'
GROUP BY 1
ORDER BY n DESC, gene
LIMIT 5000;

CREATE OR REPLACE VIEW molecular.v_clinvar_core AS
SELECT
  rcvaccession,
  genesymbol,
  clinicalsignificance,
  reviewstatus,
  numbersubmitters,
  phenotypelist,
  type AS variant_type,
  assembly, chromosome,
  start::bigint  AS pos_start,
  stop::bigint   AS pos_stop,
  referenceallele,
  alternateallele,
  cytogenetic,
  source_version,
  loaded_at
FROM molecular.clinvar_summary;
