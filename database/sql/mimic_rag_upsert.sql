-- database/sql/mimic_rag_upsert.sql
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- ── (A) Remove vocab-only dx/proc rows (no hadm_id in meta) ─────────
DELETE FROM public.rag_corpus
WHERE source IN ('mimic3_dx','mimic3_proc')
  AND (meta->>'hadm_id') IS NULL;

-- (B) MIMIC-III diagnoses
WITH src AS (
  SELECT
    'mimic3_dx'::text AS source,
    format('%s::%s::%s','mimic3_dx', d.hadm_id, COALESCE(d.seq_num,0)||':'||d.icd9_code) AS source_id,
    format('ICD-9 %s — %s', d.icd9_code, COALESCE(dic.long_title,'(unknown)'))           AS title,
    COALESCE(dic.long_title, d.icd9_code)                                                AS text,
    jsonb_build_object(
      'row_type','dx','icd_version',9,
      'subject_id', d.subject_id, 'hadm_id', d.hadm_id, 'seq_num', d.seq_num,
      'icd_code', d.icd9_code, 'long_title', COALESCE(dic.long_title,null)
    )                                                                                    AS meta
  FROM ehr_mimic3.diagnoses_icd d
  LEFT JOIN ehr_mimic3.d_icd_diagnoses dic ON dic.icd9_code = d.icd9_code
  WHERE d.icd9_code IS NOT NULL AND d.icd9_code <> ''
)
INSERT INTO public.rag_corpus(source, source_id, title, text, meta, ts)
SELECT source, source_id, title, text, meta,
       to_tsvector('english', COALESCE(title,'')||' '||COALESCE(text,''))
FROM src
ON CONFLICT (source, source_id) DO UPDATE
SET title = EXCLUDED.title,
    text  = EXCLUDED.text,
    meta  = jsonb_strip_nulls(COALESCE(public.rag_corpus.meta,'{}') || EXCLUDED.meta);

-- (C) MIMIC-III procedures
WITH src AS (
  SELECT
    'mimic3_proc'::text AS source,
    format('%s::%s::%s','mimic3_proc', p.hadm_id, COALESCE(p.seq_num,0)||':'||p.icd9_code) AS source_id,
    format('ICD-9-PROC %s — %s', p.icd9_code, COALESCE(dic.long_title,'(unknown)'))        AS title,
    COALESCE(dic.long_title, p.icd9_code)                                                  AS text,
    jsonb_build_object(
      'row_type','proc','icd_version',9,
      'subject_id', p.subject_id, 'hadm_id', p.hadm_id, 'seq_num', p.seq_num,
      'icd_code', p.icd9_code, 'long_title', COALESCE(dic.long_title,null)
    )                                                                                      AS meta
  FROM ehr_mimic3.procedures_icd p
  LEFT JOIN ehr_mimic3.d_icd_procedures dic ON dic.icd9_code = p.icd9_code
  WHERE p.icd9_code IS NOT NULL AND p.icd9_code <> ''
)
INSERT INTO public.rag_corpus(source, source_id, title, text, meta, ts)
SELECT source, source_id, title, text, meta,
       to_tsvector('english', COALESCE(title,'')||' '||COALESCE(text,''))
FROM src
ON CONFLICT (source, source_id) DO UPDATE
SET title = EXCLUDED.title,
    text  = EXCLUDED.text,
    meta  = jsonb_strip_nulls(COALESCE(public.rag_corpus.meta,'{}') || EXCLUDED.meta);

-- (D) MIMIC-IV diagnoses
WITH src AS (
  SELECT
    'mimic4_dx'::text AS source,
    format('%s::%s::%s','mimic4_dx', d.hadm_id, COALESCE(d.seq_num,0)||':'||d.icd_code||':'||d.icd_version) AS source_id,
    format('ICD-%s %s — %s', d.icd_version, d.icd_code, COALESCE(dic.long_title,'(unknown)'))               AS title,
    COALESCE(dic.long_title, d.icd_code)                                                                     AS text,
    jsonb_build_object(
      'row_type','dx',
      'icd_version', d.icd_version,
      'subject_id', d.subject_id, 'hadm_id', d.hadm_id, 'seq_num', d.seq_num,
      'icd_code', d.icd_code, 'long_title', COALESCE(dic.long_title,null)
    )                                                                                                        AS meta
  FROM ehr_mimic4.diagnoses_icd d
  LEFT JOIN ehr_mimic4.d_icd_diagnoses dic
    ON dic.icd_code=d.icd_code AND dic.icd_version=d.icd_version
  WHERE d.icd_code IS NOT NULL AND d.icd_code <> ''
)
INSERT INTO public.rag_corpus(source, source_id, title, text, meta, ts)
SELECT source, source_id, title, text, meta,
       to_tsvector('english', COALESCE(title,'')||' '||COALESCE(text,''))
FROM src
ON CONFLICT (source, source_id) DO UPDATE
SET title = EXCLUDED.title,
    text  = EXCLUDED.text,
    meta  = jsonb_strip_nulls(COALESCE(public.rag_corpus.meta,'{}') || EXCLUDED.meta);

ANALYZE public.rag_corpus;
