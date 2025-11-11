-- Admissions carrying I214 (NSTEMI) in MIMIC-IV + doc_key pattern used in RAG
WITH dx AS (
  SELECT hadm_id, subject_id, seq_num, icd_version, icd_code,
         CASE WHEN icd_version=10 AND LENGTH(icd_code)>=4
           THEN SUBSTRING(icd_code,1,3) || '.' || SUBSTRING(icd_code,4)
           ELSE icd_code END AS icd10cm_display
  FROM ehr_mimic4.diagnoses_icd
  WHERE icd_version = 10 AND icd_code = 'I214'
)
SELECT d.*,
       'mimic4_dx::' || hadm_id || '::' || seq_num || ':' || icd_code || ':' || icd_version AS doc_key
FROM dx
ORDER BY hadm_id, seq_num
LIMIT 200;

