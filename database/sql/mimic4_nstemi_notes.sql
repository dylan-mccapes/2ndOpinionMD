-- Tie I214 admissions to notes text from text.mimiciv_notes
WITH nstemi AS (
  SELECT DISTINCT hadm_id
  FROM ehr_mimic4.diagnoses_icd
  WHERE icd_version = 10 AND icd_code = 'I214'
)
SELECT
  n.subject_id,
  COALESCE(n.hadm_id, m.hadm_id) AS hadm_id,
  n.charttime,
  n.domain,
  LEFT(n.note_text, 1000) AS snippet
FROM text.mimiciv_notes n
LEFT JOIN text.mimiciv_notes_hadm_map m USING (note_id)
JOIN nstemi s ON s.hadm_id = COALESCE(n.hadm_id, m.hadm_id)
ORDER BY n.charttime
LIMIT 40;

