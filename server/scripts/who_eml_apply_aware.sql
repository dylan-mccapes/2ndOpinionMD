-- Apply AWaRe (who_aware_map.group_name) onto medicines.antibiotic_group
WITH upd AS (
  UPDATE guidelines.who_eml_medicines m
  SET antibiotic_group = w.group_name
  FROM guidelines.who_eml_atc a
  JOIN guidelines.who_aware_map w ON w.atc_code = a.atc_code
  WHERE a.med_id = m.med_id
    AND COALESCE(m.antibiotic_group,'') <> w.group_name
  RETURNING m.med_id
)
SELECT COUNT(*) AS meds_updated FROM upd;

-- Also reflect AWaRe label into existing RAG rows (idempotent)
WITH src AS (
  SELECT inn, antibiotic_group FROM guidelines.who_eml_medicines
  WHERE antibiotic_group IS NOT NULL AND antibiotic_group <> ''
),
u AS (
  UPDATE public.rag_corpus rc
  SET text = CASE
               WHEN rc.text ILIKE '%AWaRe:%' THEN rc.text
               ELSE trim(rc.text || ' AWaRe:' ||
                          (SELECT s.antibiotic_group FROM src s
                           WHERE s.inn = split_part(rc.title,'WHO EML 2025: ',2)
                           LIMIT 1))
             END
  WHERE rc.source='who_eml'
    AND EXISTS (SELECT 1 FROM src s WHERE s.inn = split_part(rc.title,'WHO EML 2025: ',2))
  RETURNING rc.id
)
SELECT COUNT(*) AS rag_rows_refreshed FROM u;
