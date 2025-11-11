-- Handy dictionary query for I214 (NSTEMI) label in MIMIC-IV
SELECT icd_code, long_title
FROM ehr_mimic4.d_icd_diagnoses
WHERE icd_code = 'I214';

