WITH x AS (
  SELECT ilx_id,
         split_part(value, ':', 1) AS system,
         split_part(value, ':', 2) AS code
  FROM ontology.neurolex_annotations
  WHERE prop_label = 'hasDbXref'
)
-- Example joins:
SELECT n.ilx_id, n.label, x.system, x.code, i.title AS icd_title, s.fsn AS snomed_fsn
FROM ontology.neurolex n
LEFT JOIN x ON x.ilx_id = n.ilx_id
LEFT JOIN ontology.icd_codes i
  ON x.system IN ('ICD10','ICD10CM','ICD9','ICD9CM')
 AND i.code = x.code
LEFT JOIN ontology.snomed_concepts s
  ON x.system IN ('SCTID','SNOMED')
 AND s.concept_id = x.code
WHERE n.ilx_id = 'ilx_0737472';

